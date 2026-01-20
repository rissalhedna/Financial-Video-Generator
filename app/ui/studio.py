"""
Fiindo Studio — Cinematic Video Creation Experience

A premium UI for generating financial videos with real-time progress,
live activity logs, and immersive video previews.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import time
import yaml

import gradio as gr

from ..models import InputData, VIDEO_STYLES, VIDEO_TYPES, SUPPORTED_STOCKS
from ..script_pipeline import generate_script_only, generate_charts
from ..video_spec import create_video


# ═══════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LogEntry:
    """Single log entry."""
    time: str
    message: str
    type: str = "info"  # info, success, highlight


@dataclass
class PipelineState:
    """Global pipeline state with activity logging."""
    topic: str = ""
    yaml_spec: Optional[Dict[str, Any]] = None
    chart_segments: List[Any] = field(default_factory=list)
    video_path: Optional[str] = None
    
    # Agent tracking
    current_agent_step: int = 0
    agent_status: str = "idle"  # idle, running, done, error
    current_phase: str = ""  # Current phase description
    
    # Activity log
    activity_log: List[LogEntry] = field(default_factory=list)
    
    # Progress tracking
    progress_pct: int = 0
    
    @property
    def segments(self) -> List[Dict]:
        return self.yaml_spec.get("segments", []) if self.yaml_spec else []
    
    def reset(self):
        self.yaml_spec = None
        self.chart_segments = []
        self.video_path = None
        self.current_agent_step = 0
        self.agent_status = "idle"
        self.current_phase = ""
        self.activity_log = []
        self.progress_pct = 0
    
    def log(self, message: str, type: str = "info"):
        """Add a log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(LogEntry(time=timestamp, message=message, type=type))
        # Keep only last 15 entries
        if len(self.activity_log) > 15:
            self.activity_log = self.activity_log[-15:]


state = PipelineState()


# ═══════════════════════════════════════════════════════════════════════════
# AGENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

AGENT_PIPELINE = [
    {"id": "intro", "name": "Introduction", "icon": "🎭", "desc": "Hook & opening"},
    {"id": "dev", "name": "Development", "icon": "📝", "desc": "Context & story"},
    {"id": "charts", "name": "Charts", "icon": "📊", "desc": "Data visualization"},
    {"id": "conclusion", "name": "Conclusion", "icon": "🎬", "desc": "Call to action"},
    {"id": "revision", "name": "Revision", "icon": "✨", "desc": "Polish & refine"},
    {"id": "visuals", "name": "Visuals", "icon": "🎨", "desc": "Visual mapping"},
]


# ═══════════════════════════════════════════════════════════════════════════
# HTML BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def agent_sidebar_html() -> str:
    """Generate the pipeline stepper with activity log."""
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
        
        html += f'''
        <div class="fi-agent-item {status}">
            <div class="fi-agent-compact">
                <span class="fi-agent-icon-sm">{agent['icon']}</span>
                <span class="fi-agent-name-sm">{agent['name']}</span>
                <span class="fi-agent-status-dot"></span>
            </div>
            </div>
        '''
    
    html += '</div>'
    
    # Add activity log
    html += activity_log_html()
    
    return html


def activity_log_html() -> str:
    """Generate live activity log."""
    if not state.activity_log:
        return ''
    
    html = '''
    <div class="fi-activity-log">
        <div class="fi-activity-header">
            <span class="dot"></span>
            Live Activity
        </div>
        <div class="fi-activity-content">
    '''
    
    for entry in reversed(state.activity_log[-10:]):
        html += f'''
        <div class="fi-log-entry {entry.type}">
            <span class="time">{entry.time}</span>
            <span class="msg">{entry.message}</span>
        </div>
        '''
    
    html += '</div></div>'
    return html


def preview_area_html() -> str:
    """Generate preview area with progress indicators."""
    if state.video_path:
        return f'''
        <div class="fi-preview-content">
            <div class="fi-preview-label">🎬 Video Ready</div>
            <div class="fi-preview-text">Your video has been rendered! Press play to watch.</div>
        </div>
        '''
    
    if state.agent_status == "running":
        phase = state.current_phase or "Processing..."
        return f'''
        <div class="fi-preview-content">
            <div class="fi-preview-label">
                <span style="animation: blink 1s infinite;">●</span> 
                {phase}
            </div>
            <div class="fi-preview-text">
                Step {state.current_agent_step} of {len(AGENT_PIPELINE)}
            </div>
            <div class="fi-progress-bar">
                <div class="fill" style="width: {state.progress_pct}%;"></div>
            </div>
        </div>
        '''
    
    if state.yaml_spec and state.yaml_spec.get("segments"):
        chart_videos = [seg.get("chart_video") for seg in state.segments if seg.get("chart_video")]
        
        if chart_videos:
            return f'''
            <div class="fi-preview-content">
                <div class="fi-preview-label">📊 Charts Rendered</div>
                <div class="fi-preview-text">
                    {len(chart_videos)} chart animation(s) ready • Click play to preview
                </div>
            </div>
            '''
        elif state.chart_segments:
            return f'''
            <div class="fi-preview-content">
                <div class="fi-preview-label">📊 Charts Pending</div>
                <div class="fi-preview-text">
                    {len(state.chart_segments)} chart(s) ready to render
                </div>
            </div>
            '''
        else:
            n = len(state.segments)
            return f'''
            <div class="fi-preview-content">
                <div class="fi-preview-label">✓ Script Complete</div>
                <div class="fi-preview-text">
                    {n} segments • Ready for video creation
                </div>
            </div>
            '''
    
        return '''
        <div class="fi-preview-empty">
            <div class="fi-preview-icon">🎬</div>
        <div class="fi-preview-text">Enter a topic and generate your video</div>
        </div>
        '''


def get_first_chart_video() -> Optional[str]:
    """Get the first chart video path from the spec."""
    if not state.yaml_spec or not state.segments:
        return None
    
    video_path = None
    
    for seg in state.segments:
        chart_path = seg.get("chart_video")
        if chart_path:
            chart_path_obj = Path(chart_path)
            if not chart_path_obj.is_absolute():
                chart_path_obj = Path.cwd() / chart_path
            if chart_path_obj.exists():
                video_path = chart_path_obj
                break
    
    # Fallback: search in charts directory
    if not video_path:
        output_dir = state.yaml_spec.get("output_dir", "out/generated")
        chart_dir = Path(output_dir) / "charts"
        if chart_dir.exists():
            chart_files = list(chart_dir.glob("*.mp4"))
            if chart_files:
                video_path = chart_files[0].absolute()
    
    if not video_path:
        return None

    # Re-encode video for browser compatibility
    return ensure_browser_compatible(video_path)


def ensure_browser_compatible(video_path: Path) -> str:
    """
    Ensure video is browser-compatible by re-encoding if needed.
    
    Manim outputs can sometimes use codecs that browsers don't play well.
    This re-encodes to H.264 with web-optimized settings.
    """
    import subprocess
    import tempfile
    
    # Create a temp file for the web-compatible version
    temp_dir = Path(tempfile.gettempdir()) / "fiindo_preview"
    temp_dir.mkdir(exist_ok=True)
    
    output_path = temp_dir / f"preview_{video_path.stem}.mp4"
    
    # Skip if already converted recently
    if output_path.exists():
        # Check if source is newer than converted
        if output_path.stat().st_mtime >= video_path.stat().st_mtime:
            return str(output_path)
    
    try:
        # Re-encode with web-compatible settings
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",  # Required for browser compatibility
            "-movflags", "+faststart",  # Enable streaming
            "-an",  # No audio for charts
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if result.returncode == 0 and output_path.exists():
            return str(output_path)
        else:
            print(f"FFmpeg warning: {result.stderr.decode()[:200]}")
            return str(video_path)
            
    except Exception as e:
        print(f"Video conversion error: {e}")
        return str(video_path)


def status_msg_html(msg: str, type: str = "info", loading: bool = False) -> str:
    """Generate animated status message."""
    icons = {"success": "✓", "error": "✕", "info": "ℹ", "warning": "⚠"}
    loading_class = " loading" if loading else ""
    return f'<div class="fi-status-{type}{loading_class}"><span>{icons.get(type, "ℹ")}</span> {msg}</div>'


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def generate_script_flow(stock_symbol: str, video_type: str, facts: str, news: str, duration: int, mood: str, voice: str, speed: str, video_style: str):
    """Generate script with real-time progress updates and activity logging."""
    global state
    
    if not stock_symbol:
        yield (
            agent_sidebar_html(),
            status_msg_html("Please select a stock", "warning"),
            preview_area_html(),
            None,
            ""
        )
        return
    
    # Build topic from stock symbol and video type
    company_name = SUPPORTED_STOCKS.get(stock_symbol, stock_symbol.split(".")[0])
    video_type_config = VIDEO_TYPES.get(video_type, VIDEO_TYPES["stock-analysis"])
    topic = f"{company_name} {video_type_config['name']}"
    
    try:
        # Reset if new topic
        if topic != state.topic:
            state.reset()
        state.topic = topic
        state.agent_status = "running"
        state.current_phase = "Initializing AI agents..."
        state.log(f"Starting generation for: {topic}", "highlight")
        
        yield (
            agent_sidebar_html(),
            status_msg_html("Initializing AI pipeline...", "info", loading=True),
            preview_area_html(),
            None,
            ""
        )
        
        # Prepare input (handle None values for optional fields)
        facts_list = [f.strip() for f in (facts or "").split("\n") if f.strip()]
        news_list = [n.strip() for n in (news or "").split("\n") if n.strip()]
        
        input_data = InputData(
            topic=topic,
            stock_symbol=stock_symbol,
            video_type=video_type,
            facts=facts_list,
            news=news_list,
            target_seconds=duration,
            video_style=video_style,
            mood=mood,
            voice_id=voice or "en-US-Studio-O",
            voice_speed=speed,
        )
        
        slug = f"{stock_symbol.lower().replace('.', '_')}_{video_type}"
        yaml_path = Path(f"videos/{slug}.yaml")
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        state.log(f"Stock: {company_name} ({stock_symbol}), Type: {video_type_config['name']}")
        
        # Progress callback
        def on_agent_progress(step: int, name: str, status: str):
            state.current_agent_step = step
            state.progress_pct = int((step / len(AGENT_PIPELINE)) * 100)
            if status == "running":
                agent = AGENT_PIPELINE[step - 1] if step > 0 else None
                if agent:
                    state.current_phase = f"{agent['icon']} {agent['name']}: {agent['desc']}"
                    state.log(f"Agent started: {agent['name']}")
            elif status == "done":
                agent = AGENT_PIPELINE[step - 1] if step > 0 else None
                if agent:
                    state.log(f"✓ {agent['name']} complete", "success")
        
        # Run pipeline in thread
        result = {"spec": None, "charts": None, "error": None}
        
        def run_pipeline():
            try:
                spec, charts = generate_script_only(
                    input_data,
                    output_path=yaml_path,
                    voice_id=voice or "en-US-Studio-O",
                    voice_speed=speed,
                    on_progress=on_agent_progress,
                )
                result["spec"] = spec
                result["charts"] = charts
            except Exception as e:
                result["error"] = e
        
        thread = threading.Thread(target=run_pipeline)
        thread.start()
        
        # Poll for updates with UI refresh
        last_step = 0
        while thread.is_alive():
            if state.current_agent_step != last_step:
                agent = AGENT_PIPELINE[state.current_agent_step - 1] if state.current_agent_step > 0 else None
                agent_name = agent["name"] if agent else "Starting"
                yield (
                    agent_sidebar_html(),
                    status_msg_html(f"Running: {agent_name}...", "info", loading=True),
                    preview_area_html(),
                    None,
                    ""
                )
                last_step = state.current_agent_step
            time.sleep(0.25)
        
        thread.join()
        
        if result["error"]:
            state.agent_status = "error"
            state.log(f"Error: {str(result['error'])}", "error")
            raise result["error"]
        
        # Success
        state.yaml_spec = result["spec"]
        state.chart_segments = result["charts"]
        state.agent_status = "done"
        state.current_phase = ""
        state.progress_pct = 100
        
        n = len(state.segments)
        charts_count = len(result["charts"])
        state.log(f"✓ Generated {n} segments, {charts_count} charts", "success")
        
        msg = f"Script ready: {n} segments"
        if charts_count > 0:
            msg += f" • {charts_count} charts to render"
        
        yield (
            agent_sidebar_html(),
            status_msg_html(msg, "success"),
            preview_area_html(),
            None,
            yaml.dump(result["spec"], default_flow_style=False, allow_unicode=True)
        )
        
    except Exception as e:
        state.agent_status = "error"
        import traceback
        traceback.print_exc()
        yield (
            agent_sidebar_html(),
            status_msg_html(f"Error: {str(e)}", "error"),
            preview_area_html(),
            None,
            ""
        )


def render_charts_flow():
    """Render charts with progress updates."""
    if not state.yaml_spec:
        yield (
            status_msg_html("Generate a script first", "warning"),
            preview_area_html(),
            None,
            ""
        )
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
        state.log("Starting chart rendering...", "highlight")
        state.current_phase = "📊 Rendering chart animations..."
        state.agent_status = "running"
        
        yield (
            status_msg_html(f"Rendering {len(state.chart_segments)} chart(s)...", "info", loading=True),
            preview_area_html(),
            None,
            ""
        )
        
        # Render charts
        state.yaml_spec = generate_charts(state.yaml_spec, state.chart_segments)
        state.agent_status = "done"
        state.current_phase = ""
        
        # Get first chart video to display
        first_chart = get_first_chart_video()
        
        state.log(f"✓ Rendered {len(state.chart_segments)} chart(s)", "success")
        
        if first_chart:
            state.log(f"Chart preview ready: {Path(first_chart).name}")
        
        yield (
            status_msg_html(f"✓ {len(state.chart_segments)} chart(s) rendered", "success"),
            preview_area_html(),
            first_chart,
            yaml.dump(state.yaml_spec, default_flow_style=False, allow_unicode=True)
        )
        
    except Exception as e:
        state.agent_status = "error"
        state.log(f"Chart error: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        yield (
            status_msg_html(f"Error: {str(e)}", "error"),
            preview_area_html(),
            None,
            ""
        )


def create_video_flow(yaml_content: str):
    """Create video with progress updates."""
    # Validate input
    if not yaml_content or not yaml_content.strip():
        yield (
            status_msg_html("Generate a script first", "warning"),
            preview_area_html(),
            None
        )
        return
    
    try:
        spec = yaml.safe_load(yaml_content)
        if not spec:
            yield (
                status_msg_html("Invalid YAML content - generate a script first", "warning"),
                preview_area_html(),
                None
            )
            return
        
        state.yaml_spec = spec
        state.agent_status = "running"
        state.log("Starting video creation...", "highlight")
        
        # Track progress with shared state
        progress_state = {"step": "", "num": 0, "total": 5}
        
        def on_video_progress(step_name: str, step_num: int, total: int):
            progress_state["step"] = step_name
            progress_state["num"] = step_num
            progress_state["total"] = total
            state.current_phase = f"🎬 {step_name}"
            state.progress_pct = int((step_num / total) * 100)
            state.log(f"Step {step_num}/{total}: {step_name}")
        
        # Initial status
        yield (
            status_msg_html("Starting video creation...", "info", loading=True),
            preview_area_html(),
            None
        )
        
        # Run video creation in a thread with progress updates
        result = {"video": None, "error": None}
        
        def run_create():
            try:
                result["video"] = create_video(
                    spec, 
                    force_refresh=False,
                    on_progress=on_video_progress
                )
            except Exception as e:
                result["error"] = e
        
        thread = threading.Thread(target=run_create)
        thread.start()
        
        # Poll for progress updates
        last_step = 0
        step_messages = {
            1: "📥 Fetching stock footage...",
            2: "🎙️ Generating voiceover...",
            3: "🎵 Adding background music...",
            4: "📝 Creating subtitles...",
            5: "🎬 Rendering final video...",
        }
        
        while thread.is_alive():
            current_step = progress_state["num"]
            if current_step != last_step and current_step > 0:
                msg = step_messages.get(current_step, f"Step {current_step}...")
                yield (
                    status_msg_html(f"{msg} ({current_step}/5)", "info", loading=True),
                    preview_area_html(),
                    None
                )
                last_step = current_step
            time.sleep(0.3)
        
        thread.join()
        
        if result["error"]:
            raise result["error"]
        
        video_path = Path(result["video"])
        if not video_path.is_absolute():
            video_path = Path.cwd() / video_path
        
        state.video_path = str(video_path)
        state.agent_status = "done"
        state.current_phase = ""
        state.progress_pct = 100
        
        state.log(f"✓ Video created: {video_path.name}", "success")
        
        # Ensure browser compatibility for final video
        playable_path = ensure_browser_compatible(video_path)
        
        yield (
            status_msg_html("✓ Video ready! Press play to watch", "success"),
            preview_area_html(),
            playable_path
        )
        
    except Exception as e:
        state.agent_status = "error"
        state.log(f"Video error: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        yield (
            status_msg_html(f"Error: {str(e)}", "error"),
            preview_area_html(),
            None
        )


# ═══════════════════════════════════════════════════════════════════════════
# UI LAYOUT
# ═══════════════════════════════════════════════════════════════════════════

def load_css() -> str:
    """Load custom CSS."""
    p = Path(__file__).parent / "styles.css"
    return p.read_text() if p.exists() else ""


def create_ui() -> gr.Blocks:
    """Create the Fiindo Studio UI."""
    
    with gr.Blocks(
        title="Fiindo Studio",
        theme=gr.themes.Base(
            primary_hue="violet",
            neutral_hue="zinc",
            font=gr.themes.GoogleFont("Space Grotesk")
        ),
        css=load_css(),
    ) as app:
        
        # Header
        gr.HTML('''
        <div class="fi-header">
            <div class="fi-logo">Fiindo Studio</div>
        </div>
        ''')
        
        # Video playback fix
        gr.HTML('''
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            function fixVideos() {
                document.querySelectorAll('video').forEach(function(video) {
                    video.setAttribute('controls', 'controls');
                    video.setAttribute('preload', 'auto');
                    video.removeAttribute('controlsList');
                    if (video.src && video.readyState === 0) video.load();
                });
            }
            fixVideos();
            setInterval(fixVideos, 1500);
            
            // Auto-scroll activity log
            const observer = new MutationObserver(function() {
                const logs = document.querySelectorAll('.fi-activity-content');
                logs.forEach(log => log.scrollTop = 0);
            });
            observer.observe(document.body, {childList: true, subtree: true});
        });
        </script>
        ''')
        
        # Main layout
        with gr.Row(elem_classes="fi-main-row"):
            
            # LEFT: Pipeline & Activity
            with gr.Column(scale=1, min_width=300, elem_classes="fi-col-left"):
                gr.HTML('<h3 style="color: var(--text-tertiary); font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 16px 0;">PIPELINE</h3>')
                agent_sidebar = gr.HTML(agent_sidebar_html())
            
            # MIDDLE: Configuration
            with gr.Column(scale=1, min_width=340, elem_classes="fi-col-middle"):
                gr.HTML('<h3 style="color: var(--text-tertiary); font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 16px 0;">CONFIGURATION</h3>')
                
                # Stock selection dropdown
                stock_choices = [(f"{name} ({symbol})", symbol) for symbol, name in SUPPORTED_STOCKS.items()]
                stock_symbol = gr.Dropdown(
                    choices=stock_choices,
                    value="AAPL.US",
                    label="Stock"
                )
                
                # Video type selection
                video_type_choices = [(config["name"], key) for key, config in VIDEO_TYPES.items()]
                video_type = gr.Radio(
                    choices=video_type_choices,
                    value="stock-analysis",
                    label="Video Type"
                )
                
                with gr.Accordion("📝 Additional Context (Optional)", open=False):
                    with gr.Row():
                        facts = gr.Textbox(label="Key Facts", placeholder="One fact per line", lines=3)
                        news = gr.Textbox(label="Recent News", placeholder="One item per line", lines=3)
                
                video_style = gr.Radio(
                    choices=[("Social Media (Short)", "social-media"), ("Documentary (Long)", "documentary")],
                    value="social-media",
                    label="Video Length"
                )
                
                with gr.Row():
                    duration = gr.Slider(30, 600, 45, step=15, label="Duration (seconds)")
                    mood = gr.Dropdown(
                        ["informative", "excited", "dramatic"],
                        value="informative",
                        label="Mood"
                    )
                
                with gr.Accordion("⚙️ Voice Settings", open=False):
                    voice = gr.Dropdown(
                        [("Studio O (Natural)", "en-US-Studio-O"), ("Neural2 J (Energetic)", "en-US-Neural2-J")],
                        value="en-US-Studio-O",
                        label="Voice"
                    )
                    speed = gr.Dropdown(["slow", "medium", "fast"], value="fast", label="Speed")
                
                gr.HTML('<hr style="border: none; border-top: 1px solid var(--border); margin: 16px 0;">')
                
                generate_btn = gr.Button("🚀 Generate Script", variant="primary", size="lg")
                
                with gr.Row():
                    charts_btn = gr.Button("📊 Render Charts", size="sm")
                    video_btn = gr.Button("🎬 Create Video", size="sm")
                
                status_display = gr.HTML(status_msg_html("Ready to create", "info"))
            
            # RIGHT: Preview
            with gr.Column(scale=1, min_width=360, elem_classes="fi-col-right"):
                gr.HTML('<h3 style="color: var(--text-tertiary); font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 16px 0;">PREVIEW</h3>')
                preview_display = gr.HTML(preview_area_html())
                
                video_output = gr.Video(
                    label=None, 
                    height=340,
                    visible=True,
                    autoplay=True,
                    show_label=False,
                    elem_classes="fi-video-player"
                )
        
        # YAML Editor
        gr.HTML('<h3 style="color: var(--text-tertiary); font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin: 24px 24px 12px 24px;">SCRIPT EDITOR</h3>')
        yaml_editor = gr.Code(language="yaml", label=None, lines=14, elem_classes="fi-yaml-editor")
        
        # Update duration when video style changes
        def update_duration_for_style(style: str):
            config = VIDEO_STYLES.get(style, VIDEO_STYLES["social-media"])
            return config["default_seconds"]
        
        video_style.change(
            update_duration_for_style,
            inputs=[video_style],
            outputs=[duration],
        )
        
        # Event handlers
        generate_btn.click(
            generate_script_flow,
            inputs=[stock_symbol, video_type, facts, news, duration, mood, voice, speed, video_style],
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
    
    return app


def launch(share=False, host="127.0.0.1", port=7860):
    """Launch the Fiindo Studio UI."""
    app = create_ui()
    app.launch(share=share, server_name=host, server_port=port, show_error=True, inbrowser=True)


if __name__ == "__main__":
    launch()
