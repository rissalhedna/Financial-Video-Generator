"""
Fiindo Studio — Clean 3-Column Layout with Expandable Agents
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import threading
import time
import yaml

import gradio as gr

from ..models import InputData
from ..script_pipeline import generate_script_only, generate_charts
from ..video_spec import create_video


# ═══════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PipelineState:
    """Global pipeline state."""
    topic: str = ""
    yaml_spec: Optional[Dict[str, Any]] = None
    chart_segments: List[Any] = field(default_factory=list)
    video_path: Optional[str] = None
    
    # Agent tracking
    current_agent_step: int = 0
    agent_status: str = "idle"  # idle, running, done, error
    
    # UI state
    expanded_agent: Optional[str] = None  # Which agent section is expanded
    
    @property
    def segments(self) -> List[Dict]:
        return self.yaml_spec.get("segments", []) if self.yaml_spec else []
    
    def reset(self):
        self.yaml_spec = None
        self.chart_segments = []
        self.video_path = None
        self.current_agent_step = 0
        self.agent_status = "idle"
        self.expanded_agent = None


state = PipelineState()


# ═══════════════════════════════════════════════════════════════════════════
# AGENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

AGENT_PIPELINE = [
    {"id": "intro", "name": "Introduction", "icon": "🎭"},
    {"id": "dev", "name": "Development", "icon": "📝"},
    {"id": "charts", "name": "Charts", "icon": "📊"},
    {"id": "conclusion", "name": "Conclusion", "icon": "🎬"},
    {"id": "revision", "name": "Revision", "icon": "✨"},
    {"id": "visuals", "name": "Visuals", "icon": "🎨"},
]


# ═══════════════════════════════════════════════════════════════════════════
# HTML BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def agent_sidebar_html() -> str:
    """Generate compact agent sidebar with expandable sections."""
    html = '<div class="fi-agent-sidebar">'
    
    for i, agent in enumerate(AGENT_PIPELINE):
        step_num = i + 1
        
        # Determine state
        if state.agent_status == "error":
            status = "error" if step_num <= state.current_agent_step else "pending"
        elif step_num < state.current_agent_step:
            status = "completed"
        elif step_num == state.current_agent_step:
            status = "running" if state.agent_status == "running" else "completed"
        else:
            status = "pending"
        
        is_expanded = state.expanded_agent == agent["id"]
        
        # Agent card (clickable)
        html += f'''
        <div class="fi-agent-item {status} {'expanded' if is_expanded else ''}" 
             onclick="document.getElementById('agent-toggle-{agent["id"]}').click()">
            <div class="fi-agent-compact">
                <span class="fi-agent-icon-sm">{agent['icon']}</span>
                <span class="fi-agent-name-sm">{agent['name']}</span>
                <span class="fi-agent-status-dot"></span>
            </div>
        '''
        
        # Expandable YAML content
        if is_expanded and state.yaml_spec:
            yaml_content = get_agent_yaml_section(agent["id"])
            html += f'''
            <div class="fi-agent-yaml">
                <pre>{yaml_content}</pre>
            </div>
            '''
        
        html += '</div>'
        
        # Hidden toggle button for Gradio
        html += f'<button id="agent-toggle-{agent["id"]}" style="display:none;"></button>'
    
    html += '</div>'
    return html


def get_agent_yaml_section(agent_id: str) -> str:
    """Extract relevant YAML section for an agent."""
    if not state.yaml_spec or not state.segments:
        return "# No content yet"
    
    # Map agent IDs to segment types
    section_map = {
        "intro": ["intro", "introduction", "hook"],
        "dev": ["development", "context", "background"],
        "charts": ["chart", "data", "statistics"],
        "conclusion": ["conclusion", "outro", "ending"],
        "revision": ["revised"],
        "visuals": state.segments,  # All segments have visuals
    }
    
    if agent_id == "visuals":
        # Show visual mappings
        visuals = []
        for seg in state.segments[:3]:  # First 3 segments
            vis = seg.get("visuals", [])
            if vis:
                visuals.append(f"- {', '.join(vis[:3])}")
        return "\n".join(visuals) if visuals else "# No visual tags yet"
    
    # Find segments for this agent
    keywords = section_map.get(agent_id, [])
    matching_segments = []
    for seg in state.segments:
        text = seg.get("text", "").lower()
        if any(kw in text[:50] for kw in keywords):
            matching_segments.append(seg)
            if len(matching_segments) >= 2:
                break
    
    if not matching_segments:
        return "# No content for this section yet"
    
    # Format as YAML
    content = []
    for seg in matching_segments:
        content.append(f"text: {seg.get('text', '')[:100]}...")
        content.append(f"emotion: {seg.get('emotion', 'neutral')}")
    
    return "\n".join(content)


def preview_area_html() -> str:
    """Generate preview area HTML."""
    if state.video_path:
        return f'''
        <div class="fi-preview-content">
            <div class="fi-preview-label">📹 Video Output</div>
            <div class="fi-preview-text">Video rendered successfully! Playing below.</div>
        </div>
        '''
    elif state.yaml_spec and state.yaml_spec.get("segments"):
        # Check if any segments have chart_video paths
        chart_videos = []
        for seg in state.segments:
            if seg.get("chart_video"):
                chart_videos.append(seg["chart_video"])
        
        if chart_videos:
            # Chart preview message (actual video plays in video_output component)
            return f'''
            <div class="fi-preview-content">
                <div class="fi-preview-label">📊 Charts Rendered</div>
                <div class="fi-preview-text">{len(chart_videos)} chart(s) generated • Playing first chart below</div>
            </div>
            '''
        elif state.chart_segments:
            return f'''
            <div class="fi-preview-content">
                <div class="fi-preview-label">📊 Charts Ready</div>
                <div class="fi-preview-text">{len(state.chart_segments)} chart(s) pending render</div>
            </div>
            '''
        else:
            n_segments = len(state.segments)
            return f'''
            <div class="fi-preview-content">
                <div class="fi-preview-label">✓ Script Generated</div>
                <div class="fi-preview-text">{n_segments} segments created</div>
            </div>
            '''
    else:
        return '''
        <div class="fi-preview-empty">
            <div class="fi-preview-icon">🎬</div>
            <div class="fi-preview-text">Previews will appear here</div>
        </div>
        '''


def get_first_chart_video() -> Optional[str]:
    """Get the first chart video path from the spec."""
    if not state.yaml_spec or not state.segments:
        return None
    
    for seg in state.segments:
        chart_path = seg.get("chart_video")
        if chart_path:
            # Ensure absolute path
            chart_path_obj = Path(chart_path)
            if not chart_path_obj.is_absolute():
                chart_path_obj = Path.cwd() / chart_path
            # Verify file exists
            if chart_path_obj.exists():
                return str(chart_path_obj)
    return None


def status_msg_html(msg: str, type: str = "info") -> str:
    """Generate status message."""
    icons = {"success": "✓", "error": "✕", "info": "ℹ", "warning": "⚠"}
    return f'<div class="fi-status-{type}"><span>{icons.get(type, "ℹ")}</span> {msg}</div>'


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def generate_script_flow(topic: str, facts: str, news: str, duration: int, mood: str, voice: str, speed: str):
    """Generate script with real-time updates."""
    global state
    
    if not topic.strip():
        yield agent_sidebar_html(), status_msg_html("Enter a topic", "warning"), preview_area_html(), None, ""
        return
    
    try:
        if topic != state.topic:
            state.reset()
        state.topic = topic
        state.agent_status = "running"
        
        yield agent_sidebar_html(), status_msg_html("Starting AI agents...", "info"), preview_area_html(), None, ""
        
        # Prepare input
        input_data = InputData(
            topic=topic,
            facts=[f.strip() for f in facts.split("\n") if f.strip()],
            news=[n.strip() for n in news.split("\n") if n.strip()],
            target_seconds=duration,
            mood=mood,
            voice_id=voice or "en-US-Studio-O",
            voice_speed=speed,
        )
        
        slug = topic.lower().replace(" ", "_").replace(".", "")[:30]
        yaml_path = Path(f"videos/{slug}.yaml")
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Progress callback
        def on_agent_progress(step: int, name: str, status: str):
            state.current_agent_step = step
        
        # Run pipeline in thread
        result = {"spec": None, "charts": None, "error": None}
        
        def run_pipeline():
            try:
                spec, charts = generate_script_only(
                    input_data, output_path=yaml_path,
                    voice_id=voice or "en-US-Studio-O",
                    voice_speed=speed, on_progress=on_agent_progress,
                )
                result["spec"] = spec
                result["charts"] = charts
            except Exception as e:
                result["error"] = e
        
        thread = threading.Thread(target=run_pipeline)
        thread.start()
        
        # Poll for updates
        last_step = 0
        while thread.is_alive():
            if state.current_agent_step != last_step:
                agent_name = AGENT_PIPELINE[state.current_agent_step - 1]["name"] if state.current_agent_step > 0 else "Starting"
                yield (
                    agent_sidebar_html(),
                    status_msg_html(f"Running: {agent_name}...", "info"),
                    preview_area_html(), None, ""
                )
                last_step = state.current_agent_step
            time.sleep(0.3)
        
        thread.join()
        
        if result["error"]:
            state.agent_status = "error"
            raise result["error"]
        
        # Success
        state.yaml_spec = result["spec"]
        state.chart_segments = result["charts"]
        state.agent_status = "done"
        
        n = len(state.segments)
        msg = f"✓ Generated {n} segments · {len(result['charts'])} charts ready"
        
        yield (
            agent_sidebar_html(),
            status_msg_html(msg, "success"),
            preview_area_html(),
            None,
            yaml.dump(result["spec"], default_flow_style=False, allow_unicode=True)
        )
        
    except Exception as e:
        state.agent_status = "error"
        import traceback; traceback.print_exc()
        yield (
            agent_sidebar_html(),
            status_msg_html(f"Error: {str(e)}", "error"),
            preview_area_html(), None, ""
        )


def toggle_agent_section(agent_id: str):
    """Toggle expansion of an agent section."""
    if state.expanded_agent == agent_id:
        state.expanded_agent = None
    else:
        state.expanded_agent = agent_id
    return agent_sidebar_html()


def render_charts_flow():
    """Render charts."""
    if not state.yaml_spec:
        yield status_msg_html("Generate script first", "warning"), preview_area_html(), None, ""
        return
    
    if not state.chart_segments:
        yield (
            status_msg_html("No charts to render", "info"),
            preview_area_html(),
            None,
            yaml.dump(state.yaml_spec, default_flow_style=False, allow_unicode=True)
        )
        return
    
    try:
        yield status_msg_html("Rendering charts...", "info"), preview_area_html(), None, ""
        
        # Render charts
        state.yaml_spec = generate_charts(state.yaml_spec, state.chart_segments)
        
        # Debug: Print segment structure
        print(f"📊 Total segments: {len(state.segments)}")
        for i, seg in enumerate(state.segments):
            print(f"📊 Segment {i}: chart_video = {seg.get('chart_video')}, is_chart_placeholder = {seg.get('is_chart_placeholder')}")
        
        # Get first chart video to display
        first_chart = get_first_chart_video()
        
        print(f"📊 Chart video path from function: {first_chart}")
        if first_chart:
            print(f"📊 Chart file exists: {Path(first_chart).exists()}")
            print(f"📊 Chart file size: {Path(first_chart).stat().st_size if Path(first_chart).exists() else 'N/A'}")
        else:
            # Try to find chart files manually
            print("📊 No chart path found in segments, searching for chart files...")
            output_dir = state.yaml_spec.get("output_dir", "out/generated")
            chart_dir = Path(output_dir) / "charts"
            if chart_dir.exists():
                chart_files = list(chart_dir.glob("*.mp4"))
                print(f"📊 Found {len(chart_files)} chart files in {chart_dir}")
                if chart_files:
                    first_chart = str(chart_files[0].absolute())
                    print(f"📊 Using first chart file: {first_chart}")
        
        yield (
            status_msg_html(f"✓ Rendered {len(state.chart_segments)} charts", "success"),
            preview_area_html(),
            first_chart,  # Display first chart in video player
            yaml.dump(state.yaml_spec, default_flow_style=False, allow_unicode=True)
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        yield status_msg_html(f"Error: {str(e)}", "error"), preview_area_html(), None, ""


def create_video_flow(yaml_content: str):
    """Create video."""
    try:
        yield status_msg_html("Creating video...", "info"), preview_area_html(), None
        spec = yaml.safe_load(yaml_content)
        state.yaml_spec = spec
        
        video = create_video(spec, force_refresh=False)
        video_path = Path(video)
        if not video_path.is_absolute():
            video_path = Path.cwd() / video_path
        
        state.video_path = str(video_path)
        
        print(f"🎬 Video path: {state.video_path}")
        print(f"🎬 Video exists: {video_path.exists()}")
        if video_path.exists():
            print(f"🎬 Video size: {video_path.stat().st_size} bytes")
            print(f"🎬 Video extension: {video_path.suffix}")
        
        # Return the path as string for Gradio
        yield status_msg_html("✓ Video created!", "success"), preview_area_html(), str(video_path)
    except Exception as e:
        import traceback; traceback.print_exc()
        yield status_msg_html(f"Error: {str(e)}", "error"), preview_area_html(), None


# ═══════════════════════════════════════════════════════════════════════════
# UI LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

def load_css() -> str:
    """Load custom CSS."""
    p = Path(__file__).parent / "styles.css"
    return p.read_text() if p.exists() else ""


def create_ui() -> gr.Blocks:
    """Create the 3-column Fiindo Studio UI."""
    
    with gr.Blocks(
        title="Fiindo Studio",
        theme=gr.themes.Base(primary_hue="violet", neutral_hue="zinc", font=gr.themes.GoogleFont("Inter")),
        css=load_css(),
    ) as app:
        
        gr.HTML('<div class="fi-header"><div class="fi-logo">🎬 Fiindo Studio</div></div>')
        
        # Add JavaScript to ensure video playback works
        gr.HTML('''
        <script>
        // Ensure video controls work properly
        document.addEventListener('DOMContentLoaded', function() {
            function fixVideos() {
                const videos = document.querySelectorAll('video');
                videos.forEach(function(video) {
                    video.setAttribute('controls', 'controls');
                    video.setAttribute('preload', 'auto');
                    video.removeAttribute('controlsList');
                    
                    // Add error handler
                    video.onerror = function() {
                        console.error('Video error:', video.error);
                    };
                    
                    // Force reload if needed
                    if (video.src && video.readyState === 0) {
                        video.load();
                    }
                });
            }
            
            // Run initially and periodically
            fixVideos();
            setInterval(fixVideos, 2000);
        });
        </script>
        ''')
        
        # 3-COLUMN LAYOUT
        with gr.Row(elem_classes="fi-main-row"):
            
            # LEFT: Agent Pipeline
            with gr.Column(scale=1, min_width=280, elem_classes="fi-col-left"):
                gr.HTML('<h3 style="color: #ffffff !important; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 16px 0;">🤖 PIPELINE</h3>')
                agent_sidebar = gr.HTML(agent_sidebar_html())
            
            # MIDDLE: Input Form (Compact)
            with gr.Column(scale=1, min_width=320, elem_classes="fi-col-middle"):
                gr.HTML('<h3 style="color: #ffffff !important; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 16px 0;">📝 CONFIGURATION</h3>')
                
                topic = gr.Textbox(label="Topic", placeholder="e.g., Tesla Stock Analysis", lines=1, elem_classes="fi-input-compact")
                
                with gr.Row():
                    facts = gr.Textbox(label="Facts", placeholder="One per line", lines=2, elem_classes="fi-input-compact")
                    news = gr.Textbox(label="News", placeholder="One per line", lines=2, elem_classes="fi-input-compact")
                
                with gr.Row():
                    duration = gr.Slider(30, 180, 60, step=10, label="Duration (s)", elem_classes="fi-compact")
                    mood = gr.Dropdown(["informative", "excited", "dramatic"], value="informative", label="Mood", elem_classes="fi-compact")
                
                with gr.Accordion("⚙️ Advanced", open=False):
                    voice = gr.Dropdown([("Studio O", "en-US-Studio-O"), ("Neural2 J", "en-US-Neural2-J")], value="en-US-Studio-O", label="Voice")
                    speed = gr.Dropdown(["slow", "medium", "fast"], value="fast", label="Speed")
                
                gr.Markdown("---")
                
                generate_btn = gr.Button("🚀 Generate Script", variant="primary", size="lg", elem_classes="fi-btn-primary")
                
                with gr.Row():
                    charts_btn = gr.Button("📊 Render Charts", size="sm")
                    video_btn = gr.Button("🎥 Create Video", size="sm")
                
                status_display = gr.HTML(status_msg_html("Ready", "info"))
            
            # RIGHT: Preview Area
            with gr.Column(scale=1, min_width=320, elem_classes="fi-col-right"):
                gr.HTML('<h3 style="color: #ffffff !important; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 16px 0;">🎬 PREVIEW</h3>')
                preview_display = gr.HTML(preview_area_html())
                
                with gr.Group():
                    video_output = gr.Video(
                        label=None, 
                        height=300, 
                        visible=True,
                        autoplay=False,
                        show_label=False,
                        elem_classes="fi-video-player"
                    )
        
        # Bottom: YAML Editor
        gr.HTML('<h3 style="color: #ffffff !important; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 20px 20px 12px 20px;">📄 YAML EDITOR</h3>')
        yaml_editor = gr.Code(language="yaml", label=None, lines=12, elem_classes="fi-yaml-editor")
        
        # EVENT HANDLERS
        generate_btn.click(
            generate_script_flow,
            inputs=[topic, facts, news, duration, mood, voice, speed],
            outputs=[agent_sidebar, status_display, preview_display, video_output, yaml_editor],
        )
        
        charts_btn.click(
            render_charts_flow,
            inputs=[],
            outputs=[status_display, preview_display, video_output, yaml_editor],
        )
        
        video_btn.click(
            create_video_flow,
            inputs=[yaml_editor],
            outputs=[status_display, preview_display, video_output],
        )
        
        # Agent toggle handlers
        for agent in AGENT_PIPELINE:
            agent_id = agent["id"]
            # This would need JavaScript or a different approach for true interactivity
            # For now, clicking updates the view but doesn't persist without a full render
    
    return app


def launch(share=False, host="127.0.0.1", port=7860):
    """Launch the Fiindo Studio UI."""
    app = create_ui()
    app.launch(share=share, server_name=host, server_port=port, show_error=True, inbrowser=True)


if __name__ == "__main__":
    launch()
