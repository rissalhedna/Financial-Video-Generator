"""
Fiindo Studio - A stunning UI for AI video generation.

Launch with: python -m app.ui.studio
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import yaml

# Import pipeline components
from ..models import InputData
from ..script_pipeline import generate_script
from ..video_spec import create_video, VideoSpec


# ============================================
# State Management
# ============================================

@dataclass
class PipelineState:
    """Tracks the current state of the generation pipeline."""
    status: str = "idle"  # idle, running, completed, error
    current_step: int = 0
    total_steps: int = 7
    step_names: List[str] = field(default_factory=lambda: [
        "Input", "Introduction", "Development", "Charts", 
        "Conclusion", "Revision", "Visual Mapping", "Rendering"
    ])
    step_status: Dict[int, str] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    # Generated content
    topic: str = ""
    facts: List[str] = field(default_factory=list)
    news: List[str] = field(default_factory=list)
    segments: List[Dict[str, Any]] = field(default_factory=list)
    yaml_spec: Optional[Dict[str, Any]] = None
    video_path: Optional[str] = None
    
    def reset(self):
        self.status = "idle"
        self.current_step = 0
        self.step_status = {}
        self.error_message = None
        self.segments = []
        self.yaml_spec = None
        self.video_path = None


# Global state
pipeline_state = PipelineState()


# ============================================
# CSS Loading
# ============================================

def load_css() -> str:
    """Load custom CSS styles."""
    css_path = Path(__file__).parent / "styles.css"
    if css_path.exists():
        return css_path.read_text()
    return ""


# ============================================
# Pipeline Execution
# ============================================

def run_generation_pipeline(
    topic: str,
    facts_text: str,
    news_text: str,
    duration: int,
    mood: str,
    voice_id: str,
    voice_speed: str,
    progress=gr.Progress()
) -> Tuple[str, str, str, str]:
    """
    Run the full generation pipeline with progress updates.
    
    Returns: (status_html, segments_html, yaml_content, video_path)
    """
    global pipeline_state
    
    try:
        pipeline_state.reset()
        pipeline_state.status = "running"
        pipeline_state.topic = topic
        pipeline_state.facts = [f.strip() for f in facts_text.split("\n") if f.strip()]
        pipeline_state.news = [n.strip() for n in news_text.split("\n") if n.strip()]
        
        # Build input
        input_data = InputData(
            topic=topic,
            facts=pipeline_state.facts,
            news=pipeline_state.news,
            target_seconds=duration,
            mood=mood,
            voice_id=voice_id if voice_id else None,
            voice_speed=voice_speed,
        )
        
        # Step 1: Generate script
        progress(0.1, desc="🚀 Starting pipeline...")
        pipeline_state.current_step = 1
        pipeline_state.step_status[1] = "running"
        
        topic_slug = topic.lower().replace(" ", "_").replace(".", "")[:30]
        yaml_path = Path(f"videos/{topic_slug}.yaml")
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        progress(0.3, desc="✍️ Generating script...")
        spec = generate_script(
            input_data,
            output_path=yaml_path,
            voice_id=voice_id or "en-US-Studio-O",
            voice_speed=voice_speed,
            music="inspirational",
        )
        
        pipeline_state.yaml_spec = spec
        pipeline_state.segments = spec.get("segments", [])
        pipeline_state.step_status[1] = "completed"
        
        # Step 2: Create video
        progress(0.5, desc="🎬 Creating video...")
        pipeline_state.current_step = 2
        pipeline_state.step_status[2] = "running"
        
        video_path = create_video(spec, force_refresh=False)
        
        pipeline_state.video_path = str(video_path)
        pipeline_state.step_status[2] = "completed"
        pipeline_state.status = "completed"
        
        progress(1.0, desc="✅ Complete!")
        
        # Generate outputs
        status_html = generate_status_html()
        segments_html = generate_segments_html()
        yaml_content = yaml.dump(spec, default_flow_style=False, allow_unicode=True)
        
        return status_html, segments_html, yaml_content, str(video_path)
        
    except Exception as e:
        pipeline_state.status = "error"
        pipeline_state.error_message = str(e)
        import traceback
        traceback.print_exc()
        
        return (
            f'<div class="status-badge error">❌ Error: {str(e)}</div>',
            "",
            "",
            None
        )


def generate_script_only(
    topic: str,
    facts_text: str,
    news_text: str,
    duration: int,
    mood: str,
    voice_id: str,
    voice_speed: str,
    progress=gr.Progress()
) -> Tuple[str, str, str]:
    """Generate just the script without creating video.
    
    Note: This still generates chart animations via Manim if the script
    includes data visualizations. The full pipeline includes:
    - 6 AI agents (intro, development, charts, conclusion, revision, visual mapping)
    - Chart video generation with Manim (if data is present)
    - YAML spec output
    """
    global pipeline_state
    
    try:
        pipeline_state.reset()
        pipeline_state.status = "running"
        pipeline_state.topic = topic
        
        input_data = InputData(
            topic=topic,
            facts=[f.strip() for f in facts_text.split("\n") if f.strip()],
            news=[n.strip() for n in news_text.split("\n") if n.strip()],
            target_seconds=duration,
            mood=mood,
            voice_id=voice_id if voice_id else None,
            voice_speed=voice_speed,
        )
        
        # Phase 1: AI Script Generation
        progress(0.1, desc="🤖 Phase 1/2: Running AI agents...")
        pipeline_state.current_step = 1
        
        topic_slug = topic.lower().replace(" ", "_").replace(".", "")[:30]
        yaml_path = Path(f"videos/{topic_slug}.yaml")
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        # This runs all 6 agents + generates chart videos
        progress(0.3, desc="✍️ Introduction agent...")
        progress(0.4, desc="📖 Development agent...")
        progress(0.5, desc="📊 Charts agent + Manim animations...")
        progress(0.6, desc="🎯 Conclusion agent...")
        progress(0.7, desc="✨ Revision agent...")
        progress(0.8, desc="🎨 Visual mapping agent...")
        
        spec = generate_script(
            input_data,
            output_path=yaml_path,
            voice_id=voice_id or "en-US-Studio-O",
            voice_speed=voice_speed,
        )
        
        pipeline_state.yaml_spec = spec
        pipeline_state.segments = spec.get("segments", [])
        pipeline_state.current_step = 2
        pipeline_state.status = "completed"
        
        progress(1.0, desc="✅ Script + charts ready!")
        
        segments_html = generate_segments_html()
        yaml_content = yaml.dump(spec, default_flow_style=False, allow_unicode=True)
        
        # Count what was generated
        num_segments = len(pipeline_state.segments)
        chart_count = sum(1 for s in pipeline_state.segments if s.get("chart_video"))
        
        status_msg = f'✅ Generated {num_segments} segments'
        if chart_count:
            status_msg += f' + {chart_count} chart animation{"s" if chart_count > 1 else ""}'
        
        return (
            f'<div class="status-badge completed">{status_msg}</div>',
            segments_html,
            yaml_content
        )
        
    except Exception as e:
        pipeline_state.status = "error"
        import traceback
        traceback.print_exc()
        return (
            f'<div class="status-badge error">❌ {str(e)}</div>',
            "",
            ""
        )


def render_from_yaml(yaml_content: str, progress=gr.Progress()) -> Tuple[str, str]:
    """Create video from edited YAML."""
    try:
        progress(0.2, desc="📝 Parsing YAML...")
        spec = yaml.safe_load(yaml_content)
        
        progress(0.4, desc="🎬 Creating video...")
        video_path = create_video(spec, force_refresh=False)
        
        progress(1.0, desc="✅ Done!")
        
        return (
            '<div class="status-badge completed">✅ Video created!</div>',
            str(video_path)
        )
    except Exception as e:
        return (
            f'<div class="status-badge error">❌ {str(e)}</div>',
            None
        )


# ============================================
# HTML Generators
# ============================================

def generate_status_html() -> str:
    """Generate pipeline status visualization showing all phases."""
    
    # Two main phases with sub-steps
    phases = [
        {
            "name": "Script Generation",
            "icon": "🤖",
            "steps": [
                ("🎣", "Hook"),
                ("📖", "Story"),
                ("📊", "Charts"),
                ("🎯", "Finale"),
                ("✨", "Polish"),
                ("🎨", "Visuals"),
            ]
        },
        {
            "name": "Video Creation",
            "icon": "🎬",
            "steps": [
                ("🔍", "Footage"),
                ("🔊", "Audio"),
                ("🎵", "Music"),
                ("🎞️", "Render"),
            ]
        }
    ]
    
    html = '<div style="padding: 20px; background: #1f2937; border-radius: 12px; border: 2px solid #4b5563;">'
    
    for phase_idx, phase in enumerate(phases):
        phase_completed = (phase_idx == 0 and pipeline_state.current_step >= 1) or \
                         (phase_idx == 1 and pipeline_state.status == "completed")
        phase_active = (phase_idx == 0 and pipeline_state.status == "running" and pipeline_state.current_step == 1) or \
                      (phase_idx == 1 and pipeline_state.status == "running" and pipeline_state.current_step == 2)
        
        # Phase colors - high contrast
        if phase_completed:
            phase_color = "#4ade80"  # Bright green
            status_text = "✓ Complete"
        elif phase_active:
            phase_color = "#c084fc"  # Bright purple
            status_text = "● Running"
        else:
            phase_color = "#9ca3af"  # Gray
            status_text = ""
        
        html += f'''
        <div style="margin-bottom: 24px;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
                <span style="font-size: 1.75rem;">{phase["icon"]}</span>
                <span style="font-size: 1.2rem; font-weight: 700; color: {phase_color};">{phase["name"]}</span>
                <span style="color: {phase_color}; font-size: 0.95rem; font-weight: 600;">{status_text}</span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 10px; padding-left: 44px;">
        '''
        
        for step_icon, step_name in phase["steps"]:
            if phase_completed:
                step_bg = "rgba(74, 222, 128, 0.2)"
                step_border = "#4ade80"
                step_text = "#4ade80"
            elif phase_active:
                step_bg = "rgba(192, 132, 252, 0.2)"
                step_border = "#c084fc"
                step_text = "#e9d5ff"
            else:
                step_bg = "#374151"
                step_border = "#4b5563"
                step_text = "#9ca3af"
            
            html += f'''
            <div style="
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 14px;
                border-radius: 8px;
                background: {step_bg};
                border: 2px solid {step_border};
                font-size: 0.9rem;
                font-weight: 600;
                color: {step_text};
            ">
                <span style="font-size: 1.1rem;">{step_icon}</span>
                <span>{step_name}</span>
            </div>
            '''
        
        html += '</div></div>'
    
    html += '</div>'
    
    return html


def generate_segments_html() -> str:
    """Generate the segments editor HTML."""
    if not pipeline_state.segments:
        return '<div style="text-align: center; color: #9ca3af; padding: 50px; font-size: 1rem;">No segments yet. Generate a script first!</div>'
    
    # High contrast emotion colors
    emotions_colors = {
        "curious": "#c084fc",     # Purple
        "dramatic": "#f87171",    # Red
        "informative": "#22d3ee", # Cyan
        "impactful": "#fbbf24",   # Yellow
        "excited": "#4ade80",     # Green
        "serious": "#818cf8",     # Indigo
        "neutral": "#9ca3af",     # Gray
    }
    
    html = '<div style="display: flex; flex-direction: column; gap: 14px;">'
    
    for i, seg in enumerate(pipeline_state.segments, 1):
        emotion = seg.get("emotion", "neutral")
        color = emotions_colors.get(emotion, "#9ca3af")
        text = seg.get("text", "")
        
        # Get visual tags
        clips = seg.get("clips", [])
        tags = []
        for clip in clips:
            if isinstance(clip, dict):
                tags.extend(clip.get("tags", []))
        
        tags_html = " ".join([
            f'<span style="background: rgba(34, 211, 238, 0.2); color: #22d3ee; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 500; border: 1px solid rgba(34, 211, 238, 0.3);">{tag}</span>'
            for tag in tags[:3]
        ])
        
        html += f'''
        <div style="
            background: #1f2937;
            border: 2px solid #4b5563;
            border-left: 4px solid {color};
            border-radius: 12px;
            padding: 18px;
            transition: all 0.2s;
        " onmouseover="this.style.borderColor='#6b7280'; this.style.transform='translateX(4px)';"
           onmouseout="this.style.borderColor='#4b5563'; this.style.transform='translateX(0)';">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="
                        background: linear-gradient(135deg, #a855f7, #3b82f6);
                        color: #ffffff;
                        width: 32px;
                        height: 32px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 0.9rem;
                        font-weight: 700;
                    ">{i}</span>
                    <span style="
                        background: {color}25;
                        color: {color};
                        padding: 6px 14px;
                        border-radius: 20px;
                        font-size: 0.85rem;
                        font-weight: 600;
                        text-transform: capitalize;
                        border: 1px solid {color}40;
                    ">🎭 {emotion}</span>
                </div>
                <span style="color: #d1d5db; font-size: 0.85rem; font-weight: 500;">
                    ~{seg.get('duration_estimate_seconds', 5)}s
                </span>
            </div>
            <p style="color: #f9fafb; font-size: 1rem; line-height: 1.7; margin: 0 0 14px 0; font-weight: 400;">
                "{text}"
            </p>
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="color: #9ca3af; font-size: 0.85rem; font-weight: 500;">🎬</span>
                {tags_html if tags_html else '<span style="color: #9ca3af; font-size: 0.85rem;">No visual tags</span>'}
            </div>
        </div>
        '''
    
    html += '</div>'
    return html


# ============================================
# Main UI Builder
# ============================================

def create_studio_ui() -> gr.Blocks:
    """Create the main Gradio interface."""
    
    custom_css = load_css()
    
    with gr.Blocks(
        title="Fiindo Studio",
        theme=gr.themes.Base(
            primary_hue="violet",
            secondary_hue="cyan",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
        css=custom_css,
    ) as demo:
        
        # Header
        gr.HTML('''
        <div class="studio-header">
            <h1 class="studio-title">🎬 Fiindo Studio</h1>
            <p class="studio-subtitle">Transform any topic into stunning financial videos with AI</p>
        </div>
        ''')
        
        # Main Layout
        with gr.Row():
            # Left Column - Input & Script
            with gr.Column(scale=1):
                
                # Topic Input Card
                with gr.Group(elem_classes="glass-card"):
                    gr.Markdown("### 💡 Topic & Content")
                    
                    topic_input = gr.Textbox(
                        label="Topic",
                        placeholder="e.g., Apple Inc stock, Tesla earnings, Bitcoin trends...",
                        lines=1,
                    )
                    
                    with gr.Row():
                        facts_input = gr.Textbox(
                            label="Facts (one per line)",
                            placeholder="Stock rose 600% since 2014\nMost valuable company\nFounded in 1976",
                            lines=4,
                        )
                        news_input = gr.Textbox(
                            label="News (one per line)",
                            placeholder="Recent earnings beat expectations\nNew product launch announced",
                            lines=4,
                        )
                    
                    with gr.Row():
                        duration_slider = gr.Slider(
                            minimum=30,
                            maximum=120,
                            value=60,
                            step=5,
                            label="Duration (seconds)",
                        )
                        mood_dropdown = gr.Dropdown(
                            choices=["informative", "excited", "dramatic", "serious", "curious"],
                            value="informative",
                            label="Mood",
                        )
                    
                    with gr.Accordion("🎙️ Voice Settings", open=False):
                        voice_dropdown = gr.Dropdown(
                            choices=[
                                ("Studio O (Natural)", "en-US-Studio-O"),
                                ("Neural2 J (Energetic)", "en-US-Neural2-J"),
                                ("Journey D (Storytelling)", "en-US-Journey-D"),
                            ],
                            value="en-US-Studio-O",
                            label="Voice",
                        )
                        speed_dropdown = gr.Dropdown(
                            choices=["slow", "medium", "fast"],
                            value="fast",
                            label="Speed",
                        )
                
                # Info about pipeline
                gr.HTML('''
                <div style="
                    background: #1f2937;
                    border: 2px solid #4b5563;
                    border-radius: 12px;
                    padding: 16px 18px;
                    margin: 14px 0;
                ">
                    <div style="display: flex; align-items: flex-start; gap: 14px;">
                        <span style="font-size: 1.5rem;">💡</span>
                        <div style="font-size: 0.95rem; color: #e5e7eb; line-height: 1.6;">
                            <strong style="color: #ffffff;">Script Generation</strong> runs 6 AI agents and creates chart animations (Manim).<br>
                            <strong style="color: #ffffff;">Video Creation</strong> then fetches footage, generates audio, and renders the final MP4.
                        </div>
                    </div>
                </div>
                ''')
                
                # Action Buttons
                with gr.Row():
                    generate_script_btn = gr.Button(
                        "✍️ Generate Script + Charts",
                        variant="secondary",
                        size="lg",
                    )
                    generate_video_btn = gr.Button(
                        "🎬 Generate Full Video",
                        variant="primary",
                        size="lg",
                    )
                
                # Status Display
                status_html = gr.HTML(
                    value='<div style="text-align: center; color: #64748b; padding: 20px;">Ready to generate</div>',
                    label="Status",
                )
                
                # Segments Editor
                with gr.Group(elem_classes="glass-card"):
                    gr.Markdown("### 📝 Script Segments")
                    segments_html = gr.HTML(
                        value='<div style="text-align: center; color: #64748b; padding: 40px;">Generate a script to see segments here</div>',
                    )
            
            # Right Column - Preview & YAML
            with gr.Column(scale=1):
                
                # Video Preview
                with gr.Group(elem_classes="glass-card"):
                    gr.Markdown("### 📺 Preview")
                    video_output = gr.Video(
                        label=None,
                        height=400,
                        autoplay=True,
                    )
                    
                    # Timeline placeholder
                    gr.HTML('''
                    <div style="background: #1f2937; border: 2px solid #4b5563; border-radius: 12px; padding: 14px; margin-top: 14px;">
                        <div style="height: 36px; background: #111827; border-radius: 8px; position: relative; overflow: hidden; border: 1px solid #374151;">
                            <div style="position: absolute; left: 0; top: 0; height: 100%; width: 0%; background: linear-gradient(90deg, #a855f7, #3b82f6); border-radius: 8px; transition: width 0.3s;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 0.85rem; color: #9ca3af; font-weight: 500;">
                            <span>0:00</span>
                            <span>0:30</span>
                            <span>1:00</span>
                        </div>
                    </div>
                    ''')
                
                # YAML Editor
                with gr.Group(elem_classes="glass-card"):
                    gr.Markdown("### 📄 YAML Specification")
                    yaml_editor = gr.Code(
                        language="yaml",
                        label=None,
                        lines=15,
                        interactive=True,
                    )
                    
                    with gr.Row():
                        render_btn = gr.Button(
                            "🔄 Render from YAML",
                            variant="secondary",
                        )
                        download_btn = gr.DownloadButton(
                            "📥 Download YAML",
                            variant="secondary",
                        )
                
                # Assets Overview
                with gr.Accordion("🎨 Assets", open=False):
                    gr.HTML('''
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; padding: 14px;">
                        <div style="background: #374151; border: 2px solid #a855f7; border-radius: 12px; padding: 20px; text-align: center;">
                            <div style="font-size: 2.5rem;">📹</div>
                            <div style="color: #ffffff; font-weight: 700; margin-top: 10px; font-size: 1rem;">Videos</div>
                            <div style="color: #d1d5db; font-size: 0.9rem; margin-top: 4px;">Stock footage</div>
                        </div>
                        <div style="background: #374151; border: 2px solid #06b6d4; border-radius: 12px; padding: 20px; text-align: center;">
                            <div style="font-size: 2.5rem;">🔊</div>
                            <div style="color: #ffffff; font-weight: 700; margin-top: 10px; font-size: 1rem;">Audio</div>
                            <div style="color: #d1d5db; font-size: 0.9rem; margin-top: 4px;">TTS segments</div>
                        </div>
                        <div style="background: #374151; border: 2px solid #22c55e; border-radius: 12px; padding: 20px; text-align: center;">
                            <div style="font-size: 2.5rem;">📊</div>
                            <div style="color: #ffffff; font-weight: 700; margin-top: 10px; font-size: 1rem;">Charts</div>
                            <div style="color: #d1d5db; font-size: 0.9rem; margin-top: 4px;">Animated data</div>
                        </div>
                    </div>
                    ''')
        
        # Footer
        gr.HTML('''
        <div style="text-align: center; padding: 28px; margin-top: 28px; border-top: 2px solid #4b5563;">
            <p style="color: #9ca3af; font-size: 0.95rem; margin: 0; font-weight: 500;">
                🎬 Fiindo Studio • AI-Powered Financial Video Generation
            </p>
        </div>
        ''')
        
        # Event Handlers
        generate_script_btn.click(
            fn=generate_script_only,
            inputs=[
                topic_input, facts_input, news_input,
                duration_slider, mood_dropdown,
                voice_dropdown, speed_dropdown,
            ],
            outputs=[status_html, segments_html, yaml_editor],
            show_progress="full",
        )
        
        generate_video_btn.click(
            fn=run_generation_pipeline,
            inputs=[
                topic_input, facts_input, news_input,
                duration_slider, mood_dropdown,
                voice_dropdown, speed_dropdown,
            ],
            outputs=[status_html, segments_html, yaml_editor, video_output],
            show_progress="full",
        )
        
        render_btn.click(
            fn=render_from_yaml,
            inputs=[yaml_editor],
            outputs=[status_html, video_output],
            show_progress="full",
        )
    
    return demo


def launch_studio(
    share: bool = False,
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
):
    """Launch the Fiindo Studio UI."""
    demo = create_studio_ui()
    demo.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        show_error=True,
    )


# CLI Entry Point
if __name__ == "__main__":
    import typer
    
    app = typer.Typer(help="Fiindo Studio - AI Video Generation UI")
    
    @app.command()
    def main(
        share: bool = typer.Option(False, "--share", help="Create a public link"),
        host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
        port: int = typer.Option(7860, "--port", help="Server port"),
    ):
        """Launch Fiindo Studio."""
        print("🎬 Starting Fiindo Studio...")
        launch_studio(share=share, server_name=host, server_port=port)
    
    app()

