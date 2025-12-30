"""Video Creator Agent - Modern Dashboard UI"""
from __future__ import annotations

import datetime as dt
import hmac
import math
import random
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import streamlit as st
import yaml
from src.utils.ffmpeg import (
    build_drawtext_filter,
    generate_color_image,
    render_image_with_text,
)
from src.providers.youtube_oauth import (
    render_youtube_login,
    credentials_configured,
    save_token_to_file,
    get_channel_info,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.yaml"
SECRETS_DIR = ROOT / "secrets"
ASSETS_DIR = ROOT / "assets"
RUNS_UI_DIR = ROOT / "runs" / "_ui"
SCHEDULE_PID_PATH = RUNS_UI_DIR / "scheduler.pid"
SCHEDULE_LOG_PATH = RUNS_UI_DIR / "scheduler.log"
FULLRUN_PID_PATH = RUNS_UI_DIR / "full_run.pid"
FULLRUN_LOG_PATH = RUNS_UI_DIR / "full_run.log"

# ─────────────────────────────────────────────────────────────────────────────
# Modern Dark Theme CSS
# ─────────────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Root variables */
    :root {
        --bg-primary: #0a0a0f;
        --bg-secondary: #12121a;
        --bg-card: rgba(255, 255, 255, 0.03);
        --bg-card-hover: rgba(255, 255, 255, 0.06);
        --border-color: rgba(255, 255, 255, 0.08);
        --text-primary: #ffffff;
        --text-secondary: rgba(255, 255, 255, 0.7);
        --text-muted: rgba(255, 255, 255, 0.4);
        --accent-primary: #6366f1;
        --accent-secondary: #8b5cf6;
        --accent-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        --success: #22c55e;
        --warning: #f59e0b;
        --error: #ef4444;
        --glass-bg: rgba(255, 255, 255, 0.02);
        --glass-border: rgba(255, 255, 255, 0.1);
    }

    /* Main container */
    .stApp {
        background: var(--bg-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: var(--text-secondary);
    }

    /* Headers */
    h1, h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }

    h1 {
        font-size: 2rem !important;
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-card);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
        border: 1px solid var(--border-color);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: var(--text-secondary);
        font-weight: 500;
        padding: 8px 16px;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background: var(--accent-gradient) !important;
        color: white !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1.5rem;
    }

    /* Card styling */
    .status-card {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 1.25rem;
        backdrop-filter: blur(10px);
        transition: all 0.2s ease;
    }

    .status-card:hover {
        background: var(--bg-card-hover);
        border-color: rgba(255, 255, 255, 0.15);
    }

    .status-card h4 {
        color: var(--text-muted);
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .status-card .value {
        color: var(--text-primary);
        font-size: 1.5rem;
        font-weight: 600;
    }

    .status-running {
        border-left: 3px solid var(--success);
    }

    .status-idle {
        border-left: 3px solid var(--text-muted);
    }

    .status-error {
        border-left: 3px solid var(--error);
    }

    /* Button styling */
    .stButton > button {
        background: var(--accent-gradient);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.25rem;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Secondary button */
    .secondary-btn > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: none !important;
    }

    .secondary-btn > button:hover {
        background: var(--bg-card-hover) !important;
        border-color: var(--accent-primary) !important;
    }

    /* Form inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        padding: 0.75rem 1rem !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }

    /* Labels */
    .stTextInput > label,
    .stTextArea > label,
    .stNumberInput > label,
    .stSelectbox > label,
    .stCheckbox > label,
    .stMultiSelect > label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
    }

    /* Checkbox styling */
    .stCheckbox > label > span {
        color: var(--text-secondary) !important;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }

    /* Divider */
    hr {
        border-color: var(--border-color) !important;
        margin: 2rem 0 !important;
    }

    /* Success/Error/Warning messages */
    .stSuccess {
        background: rgba(34, 197, 94, 0.1) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        border-radius: 10px !important;
    }

    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: 10px !important;
    }

    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        border-radius: 10px !important;
    }

    .stInfo {
        background: rgba(99, 102, 241, 0.1) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-radius: 10px !important;
    }

    /* Metric styling */
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-muted) !important;
    }

    /* Code blocks */
    code {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
        color: var(--accent-secondary) !important;
        padding: 0.2rem 0.4rem !important;
    }

    pre {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
    }

    /* Caption styling */
    .stCaption {
        color: var(--text-muted) !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: var(--bg-card) !important;
        border: 1px dashed var(--border-color) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }

    /* Multiselect */
    .stMultiSelect > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
    }

    /* Progress bar */
    .stProgress > div > div {
        background: var(--accent-gradient) !important;
        border-radius: 10px !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header {
        visibility: hidden;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.2);
    }

    /* Animation for status indicators */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .pulse {
        animation: pulse 2s infinite;
    }

    /* Quick action grid */
    .action-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
    }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Presets
# ─────────────────────────────────────────────────────────────────────────────
PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "Cafe Steam": {
        "visuals": {
            "image_provider": "openai",
            "image_prompt": (
                "cozy coffee shop interior, warm light, soft steam, cinematic, "
                "empty center space for title text \"{overlay_text}\", high detail"
            ),
            "openai_model": "gpt-image-1",
            "openai_size": "1792x1024",
            "loop_motion_style": "cinematic",
            "loop_zoom_amount": 0.015,
            "loop_pan_amount": 0.08,
            "loop_effects": ["steam", "flicker", "vignette"],
            "loop_flicker_amount": 0.01,
            "loop_vignette_angle": "PI/5",
            "loop_steam_opacity": 0.08,
            "loop_steam_blur": 10.0,
            "loop_steam_noise": 12,
            "loop_steam_drift_x": 0.02,
            "loop_steam_drift_y": 0.05,
        },
        "text_overlay": {
            "text": "LOCK IN",
            "auto_texts": ["LOCK IN", "HYPER FOCUS", "SLOW DOWN"],
            "auto_mode": "daily",
            "apply_to_video": False,
            "create_thumbnail": True,
            "upload_thumbnail": True,
            "font_size": 96,
            "x": "(w-text_w)/2",
            "y": "(h-text_h)/2",
        },
        "upload": {
            "title_template": "Cafe Steam Chill Mix - Cozy Coffee Shop Ambience - {date}",
            "description_template": (
                "Relaxing cafe ambience with gentle steam drift visuals.\n"
                "Perfect for study, focus, reading, and sleep.\n\n"
                "New mix daily."
            ),
            "tags": [
                "cafe ambience", "coffee shop ambience", "study music",
                "focus music", "relaxing mix", "lofi", "chill beats",
                "background music", "sleep music",
            ],
            "category_id": "10",
        },
    },
    "Fireplace Lounge": {
        "visuals": {
            "image_provider": "openai",
            "image_prompt": (
                "cozy fireplace living room, warm glow, winter evening, "
                "empty center space for text, high detail, cinematic"
            ),
            "loop_motion_style": "smooth",
            "loop_effects": ["flicker", "vignette"],
            "loop_flicker_amount": 0.02,
        },
        "text_overlay": {
            "auto_texts": ["RELAX", "UNWIND", "REST"],
            "auto_mode": "daily",
        },
        "upload": {
            "title_template": "Fireplace Lounge - Cozy Evening Mix - {date}",
            "tags": ["fireplace", "cozy", "relaxing", "evening", "ambient"],
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_app_password() -> str:
    try:
        if "app_password" in st.secrets:
            return str(st.secrets["app_password"]).strip()
    except FileNotFoundError:
        pass
    return os.getenv("APP_PASSWORD", "").strip()


def ensure_runs_dir() -> None:
    RUNS_UI_DIR.mkdir(parents=True, exist_ok=True)


def read_pid(pid_path: Path) -> int | None:
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def get_job_status(pid_path: Path) -> tuple[bool, int | None]:
    """Returns (is_running, pid)"""
    pid = read_pid(pid_path)
    if pid and is_pid_running(pid):
        return True, pid
    return False, None


def start_background(args: list[str], pid_path: Path, log_path: Path) -> int:
    ensure_runs_dir()
    existing_pid = read_pid(pid_path)
    if existing_pid and is_pid_running(existing_pid):
        return existing_pid

    log_handle = log_path.open("a", encoding="utf-8")
    kwargs: dict[str, Any] = {"stdout": log_handle, "stderr": log_handle}
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(args, **kwargs)
    log_handle.close()
    pid_path.write_text(str(process.pid), encoding="utf-8")
    return process.pid


def stop_background(pid_path: Path) -> bool:
    pid = read_pid(pid_path)
    if not pid:
        return False
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, text=True, check=False,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    try:
        pid_path.unlink()
    except FileNotFoundError:
        pass
    return True


def run_agent_once_cli(
    config_path: Path,
    test_mode: bool = False,
    test_minutes: int | None = None,
) -> tuple[int, str]:
    args = [sys.executable, "-m", "src.agent", "--config", str(config_path), "--once"]
    if test_mode:
        args.append("--test")
    if test_minutes:
        args += ["--test-minutes", str(test_minutes)]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    output = (result.stdout or "").strip()
    if result.stderr:
        output = f"{output}\n{result.stderr.strip()}".strip()
    return result.returncode, output


def require_password() -> bool:
    app_password = get_app_password()
    if not app_password:
        return True
    if st.session_state.get("password_ok"):
        return True

    def password_entered() -> None:
        entered = st.session_state.get("password", "")
        if hmac.compare_digest(entered, app_password):
            st.session_state["password_ok"] = True
            st.session_state["password"] = ""
        else:
            st.session_state["password_ok"] = False

    st.markdown("### Enter Password")
    st.text_input(
        "App password",
        type="password",
        on_change=password_entered,
        key="password",
        label_visibility="collapsed",
    )
    if st.session_state.get("password_ok") is False:
        st.error("Incorrect password")
    return st.session_state.get("password_ok", False)


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if EXAMPLE_CONFIG_PATH.exists():
        return yaml.safe_load(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return {}


def save_config(config: dict[str, Any]) -> None:
    text = yaml.safe_dump(config, sort_keys=False)
    CONFIG_PATH.write_text(text, encoding="utf-8")


def cfg(config: dict[str, Any], section: str, key: str, default: Any) -> Any:
    return config.get(section, {}).get(key, default)


def path_for_config(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def save_uploaded_file(upload, dest_path: Path) -> str:
    if upload is None:
        return ""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(upload.getvalue())
    return path_for_config(dest_path)


def split_tags(text: str) -> list[str]:
    return [tag.strip() for tag in text.split(",") if tag.strip()]


def split_text_lines(text: str) -> list[str]:
    if not text:
        return []
    entries: list[str] = []
    for line in text.splitlines():
        entries.extend(line.split(","))
    return [item.strip() for item in entries if item.strip()]


def select_overlay_text(overlay_text: str, auto_texts: list[str], mode: str) -> str:
    if overlay_text.strip():
        return overlay_text.strip()
    if not auto_texts:
        return ""
    mode = mode.strip().lower()
    if mode == "random":
        return random.choice(auto_texts)
    idx = dt.date.today().toordinal() % len(auto_texts)
    return auto_texts[idx]


def resolve_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def safe_float(value: Any, default: float) -> float:
    """Safely convert a value to float, supporting PI expressions."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            pass
        normalized = re.sub(r"\s+", "", text).upper()
        if normalized == "PI":
            return math.pi
        match = re.match(r"^PI([/*])([0-9.]+)$", normalized)
        if match:
            op, num_str = match.groups()
            try:
                number = float(num_str)
            except ValueError:
                return default
            return math.pi / number if op == "/" else math.pi * number
        match = re.match(r"^([0-9.]+)([/*])PI$", normalized)
        if match:
            num_str, op = match.groups()
            try:
                number = float(num_str)
            except ValueError:
                return default
            return number / math.pi if op == "/" else number * math.pi
    return default


def default_fontfile() -> Path | None:
    if os.name != "nt":
        return None
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def apply_preset(config: dict[str, Any], preset: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for section, values in preset.items():
        section_map = config.setdefault(section, {})
        section_map.update(values)
    return config


def get_recent_runs() -> list[Path]:
    """Get list of recent run directories"""
    runs_dir = ROOT / "runs"
    if not runs_dir.exists():
        return []
    dirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name != "_ui" and d.name != "_preview"]
    return sorted(dirs, key=lambda x: x.stat().st_mtime, reverse=True)[:5]


def get_log_tail(log_path: Path, lines: int = 20) -> str:
    """Get last N lines of a log file"""
    if not log_path.exists():
        return ""
    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
        return "\n".join(content.splitlines()[-lines:])
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# UI Components
# ─────────────────────────────────────────────────────────────────────────────

def render_status_card(title: str, value: str, status: str = "idle") -> None:
    """Render a status card with title, value, and status indicator"""
    status_class = f"status-{status}"
    st.markdown(f"""
        <div class="status-card {status_class}">
            <h4>{title}</h4>
            <div class="value">{value}</div>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar(config: dict[str, Any], demo_mode: bool) -> dict[str, bool]:
    """Render the sidebar with status and controls. Returns action flags."""
    actions = {
        "run_test": False,
        "run_full": False,
        "run_preview": False,
        "stop_full": False,
        "start_schedule": False,
        "stop_schedule": False,
    }

    st.sidebar.markdown("## Controls")

    # Status indicators
    full_running, full_pid = get_job_status(FULLRUN_PID_PATH)
    sched_running, sched_pid = get_job_status(SCHEDULE_PID_PATH)

    # Full run status
    if full_running:
        st.sidebar.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 1rem;">
                <span style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%; display: inline-block;" class="pulse"></span>
                <span style="color: #22c55e; font-weight: 500;">Full Run Active</span>
                <span style="color: rgba(255,255,255,0.4); font-size: 0.8rem;">PID {full_pid}</span>
            </div>
        """, unsafe_allow_html=True)

    # Schedule status
    if sched_running:
        daily_time = cfg(config, "schedule", "daily_time", "03:00")
        st.sidebar.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 1rem;">
                <span style="width: 8px; height: 8px; background: #6366f1; border-radius: 50%; display: inline-block;" class="pulse"></span>
                <span style="color: #8b5cf6; font-weight: 500;">Scheduled @ {daily_time}</span>
            </div>
        """, unsafe_allow_html=True)

    st.sidebar.markdown("---")

    # Quick actions
    st.sidebar.markdown("### Quick Actions")

    col1, col2, col3 = st.sidebar.columns(3)

    with col1:
        if st.button("Preview", disabled=demo_mode, use_container_width=True, key="sidebar_preview", help="30-sec sample"):
            actions["run_preview"] = True

    with col2:
        if st.button("Test", disabled=demo_mode, use_container_width=True, key="sidebar_test", help="10-min test"):
            actions["run_test"] = True

    with col3:
        if full_running:
            if st.button("Stop", disabled=demo_mode, use_container_width=True, key="sidebar_stop_full"):
                actions["stop_full"] = True
        else:
            if st.button("Full", disabled=demo_mode, use_container_width=True, key="sidebar_full", help="Full render"):
                actions["run_full"] = True

    # Schedule control
    st.sidebar.markdown("### Schedule")
    if sched_running:
        if st.sidebar.button("Stop Schedule", disabled=demo_mode, use_container_width=True, key="sidebar_stop_sched"):
            actions["stop_schedule"] = True
    else:
        if st.sidebar.button("Start Schedule", disabled=demo_mode, use_container_width=True, key="sidebar_start_sched"):
            actions["start_schedule"] = True

    st.sidebar.markdown("---")

    # Demo mode toggle
    demo_mode = st.sidebar.checkbox(
        "Demo mode",
        value=demo_mode,
        help="Preview only - no saving or running"
    )
    if demo_mode:
        st.sidebar.info("Saving is disabled")

    st.sidebar.markdown("---")

    # YouTube Account Status
    st.sidebar.markdown("### YouTube Account")
    if credentials_configured():
        if "youtube_token" in st.session_state and st.session_state.youtube_token:
            channel = get_channel_info(st.session_state.youtube_token)
            if channel:
                st.sidebar.success(f"**{channel['title']}**")
                if st.sidebar.button("Logout", key="sidebar_yt_logout", use_container_width=True):
                    st.session_state.youtube_token = None
                    st.rerun()
            else:
                st.sidebar.warning("Session expired")
                token = render_youtube_login()
        else:
            token = render_youtube_login()
            if token:
                st.rerun()
    else:
        st.sidebar.info("Configure OAuth in Settings")
        with st.sidebar.expander("Quick Setup"):
            st.markdown("""
            1. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in Streamlit secrets
            2. Add your app URL as redirect URI in Google Cloud Console
            """)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Today: {dt.date.today().isoformat()}")

    return actions


def render_dashboard_tab(config: dict[str, Any]) -> None:
    """Render the dashboard/overview tab"""

    # Status cards row
    col1, col2, col3 = st.columns(3)

    full_running, _ = get_job_status(FULLRUN_PID_PATH)
    sched_running, _ = get_job_status(SCHEDULE_PID_PATH)

    with col1:
        status = "running" if full_running else "idle"
        value = "Running" if full_running else "Idle"
        render_status_card("Full Run", value, status)

    with col2:
        status = "running" if sched_running else "idle"
        value = cfg(config, "schedule", "daily_time", "03:00") if sched_running else "Off"
        render_status_card("Schedule", value, status)

    with col3:
        recent = get_recent_runs()
        if recent:
            last_run = recent[0].name
            render_status_card("Last Run", last_run[:10], "idle")
        else:
            render_status_card("Last Run", "None", "idle")

    st.markdown("---")

    # Quick config summary
    st.markdown("### Current Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Audio**")
        source = cfg(config, "audio", "source", "local")
        if source == "local":
            folder = cfg(config, "audio", "local_folder", "Not set")
            st.caption(f"Local: `{folder}`")
        else:
            folder_id = cfg(config, "audio", "drive_folder_id", "Not set")
            st.caption(f"Drive: `{folder_id[:20]}...`" if len(str(folder_id)) > 20 else f"Drive: `{folder_id}`")

        minutes_min = cfg(config, "audio", "target_minutes_min", None)
        minutes_max = cfg(config, "audio", "target_minutes_max", None)
        if minutes_min is not None:
            st.caption(f"Duration: {minutes_min}-{minutes_max} minutes")
        else:
            hours_min = cfg(config, "audio", "target_hours_min", 8)
            hours_max = cfg(config, "audio", "target_hours_max", 9)
            st.caption(f"Duration: {hours_min}-{hours_max} hours")

    with col2:
        st.markdown("**Visuals**")
        image_provider = cfg(config, "visuals", "image_provider", "openai")
        loop_provider = cfg(config, "visuals", "loop_provider", "ffmpeg")
        st.caption(f"Image: {image_provider}")
        st.caption(f"Loop: {loop_provider}")

        effects = cfg(config, "visuals", "loop_effects", [])
        if effects:
            st.caption(f"Effects: {', '.join(effects)}")

    st.markdown("---")

    # Recent runs
    st.markdown("### Recent Runs")
    recent = get_recent_runs()
    if recent:
        for run_dir in recent[:5]:
            output_files = list(run_dir.glob("*.mp4"))
            status_icon = "" if output_files else ""
            st.markdown(f"`{run_dir.name}` {status_icon}")
    else:
        st.caption("No runs yet")

    # Logs viewer
    if full_running or FULLRUN_LOG_PATH.exists():
        with st.expander("View Full Run Log"):
            log_content = get_log_tail(FULLRUN_LOG_PATH, 30)
            if log_content:
                st.code(log_content, language="text")
            else:
                st.caption("No log content")

    if sched_running or SCHEDULE_LOG_PATH.exists():
        with st.expander("View Schedule Log"):
            log_content = get_log_tail(SCHEDULE_LOG_PATH, 30)
            if log_content:
                st.code(log_content, language="text")
            else:
                st.caption("No log content")


def render_audio_tab(config: dict[str, Any]) -> dict[str, Any]:
    """Render audio configuration tab"""
    audio_config = {}

    st.markdown("### Audio Source")

    audio_source_label = st.selectbox(
        "Source",
        ["Local folder", "Google Drive"],
        index=0 if cfg(config, "audio", "source", "drive") == "local" else 1,
    )
    audio_config["source"] = "local" if audio_source_label == "Local folder" else "drive"

    if audio_config["source"] == "local":
        col1, col2 = st.columns([3, 1])
        with col1:
            audio_config["local_folder"] = st.text_input(
                "Folder path",
                cfg(config, "audio", "local_folder", ""),
                placeholder="C:\\Users\\Music or /home/user/music"
            )
        with col2:
            audio_config["recursive"] = st.checkbox(
                "Recursive",
                value=bool(cfg(config, "audio", "recursive", False)),
                help="Scan subfolders"
            )

        audio_config["uploaded_files"] = st.file_uploader(
            "Or upload MP3 files",
            type=["mp3"],
            accept_multiple_files=True,
        )
    else:
        audio_config["drive_folder_id"] = st.text_input(
            "Google Drive folder ID",
            cfg(config, "audio", "drive_folder_id", ""),
            help="The ID from the Drive folder URL"
        )
        audio_config["local_folder"] = cfg(config, "audio", "local_folder", "")
        audio_config["recursive"] = cfg(config, "audio", "recursive", False)
        audio_config["uploaded_files"] = []

    st.markdown("### Playlist Settings")

    col1, col2 = st.columns(2)
    with col1:
        audio_config["ordering"] = st.selectbox(
            "Ordering",
            ["name", "modifiedTime"],
            index=0 if cfg(config, "audio", "ordering", "name") == "name" else 1,
        )
    with col2:
        audio_config["repeat_playlist"] = st.checkbox(
            "Repeat to fill duration",
            value=bool(cfg(config, "audio", "repeat_playlist", True)),
        )

    # Duration mode selector
    has_minutes_config = cfg(config, "audio", "target_minutes_min", None) is not None
    duration_mode = st.radio(
        "Duration unit",
        ["Hours", "Minutes"],
        index=1 if has_minutes_config else 0,
        horizontal=True,
        disabled=not audio_config["repeat_playlist"],
    )

    col1, col2 = st.columns(2)
    if duration_mode == "Hours":
        with col1:
            audio_config["target_hours_min"] = st.number_input(
                "Min hours",
                min_value=0.0, max_value=24.0, step=0.5,
                value=float(cfg(config, "audio", "target_hours_min", 8)),
                disabled=not audio_config["repeat_playlist"],
            )
        with col2:
            audio_config["target_hours_max"] = st.number_input(
                "Max hours",
                min_value=0.0, max_value=24.0, step=0.5,
                value=float(cfg(config, "audio", "target_hours_max", 9)),
                disabled=not audio_config["repeat_playlist"],
            )
        audio_config["target_minutes_min"] = None
        audio_config["target_minutes_max"] = None
    else:
        with col1:
            audio_config["target_minutes_min"] = st.number_input(
                "Min minutes",
                min_value=0, max_value=1440,
                value=int(cfg(config, "audio", "target_minutes_min", 10)),
                disabled=not audio_config["repeat_playlist"],
                help="For quick tests: 5-30 min. For shorts: 60 min."
            )
        with col2:
            audio_config["target_minutes_max"] = st.number_input(
                "Max minutes",
                min_value=0, max_value=1440,
                value=int(cfg(config, "audio", "target_minutes_max", 15)),
                disabled=not audio_config["repeat_playlist"],
            )
        audio_config["target_hours_min"] = None
        audio_config["target_hours_max"] = None

    with st.expander("Audio Quality"):
        col1, col2 = st.columns(2)
        with col1:
            audio_config["concat_quality"] = st.number_input(
                "Quality (0=best, 9=worst)",
                min_value=0, max_value=9,
                value=int(cfg(config, "audio", "concat_quality", 2)),
            )
        with col2:
            audio_config["concat_bitrate"] = st.text_input(
                "Bitrate (optional)",
                cfg(config, "audio", "concat_bitrate", "") or "",
                placeholder="192k"
            )

    # Drive credentials (only if Drive source)
    if audio_config["source"] == "drive":
        with st.expander("Drive Credentials"):
            audio_config["use_service_account"] = st.checkbox(
                "Use service account",
                value=bool(cfg(config, "drive", "use_service_account", True)),
            )
            if audio_config["use_service_account"]:
                audio_config["service_account_json"] = st.text_input(
                    "Service account JSON path",
                    cfg(config, "drive", "service_account_json", "secrets/drive_service_account.json"),
                )
                audio_config["upload_sa"] = st.file_uploader("Upload service account JSON", type=["json"])
            else:
                audio_config["oauth_client_json"] = st.text_input(
                    "OAuth client JSON path",
                    cfg(config, "drive", "oauth_client_json", "secrets/drive_oauth_client.json"),
                )
                audio_config["token_json"] = st.text_input(
                    "Token JSON path",
                    cfg(config, "drive", "token_json", "secrets/drive_token.json"),
                )
                audio_config["upload_oauth"] = st.file_uploader("Upload OAuth client JSON", type=["json"])

    return audio_config


def render_visuals_tab(config: dict[str, Any]) -> dict[str, Any]:
    """Render visuals configuration tab"""
    visuals = {}

    # Image source
    st.markdown("### Image")

    col1, col2 = st.columns(2)
    with col1:
        visuals["auto_background"] = st.checkbox(
            "Auto-generate background",
            value=bool(cfg(config, "visuals", "auto_background", False)),
            help="Generate solid color background"
        )
    with col2:
        if visuals["auto_background"]:
            visuals["background_color"] = st.text_input(
                "Background color",
                cfg(config, "visuals", "background_color", "black"),
            )

    if not visuals["auto_background"]:
        visuals["image_path"] = st.text_input(
            "Image path (leave blank to generate)",
            cfg(config, "visuals", "image_path", "") or "",
        )
        visuals["upload_image"] = st.file_uploader("Or upload image", type=["png", "jpg", "jpeg"])

        if not visuals.get("image_path"):
            visuals["image_provider"] = st.selectbox(
                "Image generator",
                ["openai", "whisk"],
                index=0 if cfg(config, "visuals", "image_provider", "openai") == "openai" else 1,
            )
            visuals["image_prompt"] = st.text_area(
                "Image prompt",
                cfg(config, "visuals", "image_prompt", "cozy coffee shop interior, warm light, cinematic"),
                height=80,
            )
            st.caption("Use `{overlay_text}` and `{date}` as placeholders")

            if visuals["image_provider"] == "openai":
                with st.expander("OpenAI Settings"):
                    col1, col2 = st.columns(2)
                    with col1:
                        visuals["openai_model"] = st.text_input(
                            "Model",
                            cfg(config, "visuals", "openai_model", "gpt-image-1"),
                        )
                    with col2:
                        visuals["openai_size"] = st.selectbox(
                            "Size",
                            ["1792x1024", "1024x1024", "1024x1792"],
                            index=0,
                        )

    st.markdown("---")

    # Loop video
    st.markdown("### Loop Video")

    visuals["loop_video_path"] = st.text_input(
        "Loop video path (leave blank to generate)",
        cfg(config, "visuals", "loop_video_path", "") or "",
    )
    visuals["upload_loop"] = st.file_uploader("Or upload loop video", type=["mp4", "mov"])

    if not visuals.get("loop_video_path"):
        visuals["loop_provider"] = st.selectbox(
            "Loop generator",
            ["ffmpeg", "grok"],
            index=0 if cfg(config, "visuals", "loop_provider", "ffmpeg") == "ffmpeg" else 1,
        )

        if visuals["loop_provider"] == "ffmpeg":
            col1, col2, col3 = st.columns(3)
            with col1:
                visuals["loop_duration_seconds"] = st.number_input(
                    "Duration (sec)",
                    min_value=1, max_value=30,
                    value=int(cfg(config, "visuals", "loop_duration_seconds", 5)),
                )
            with col2:
                visuals["fps"] = st.number_input(
                    "FPS",
                    min_value=1, max_value=60,
                    value=int(cfg(config, "visuals", "fps", 30)),
                )
            with col3:
                visuals["loop_motion_style"] = st.selectbox(
                    "Motion style",
                    ["smooth", "cinematic", "orbit"],
                    index=1,
                )

            col1, col2 = st.columns(2)
            with col1:
                visuals["loop_zoom_amount"] = st.slider(
                    "Zoom amount",
                    min_value=0.0, max_value=0.1, step=0.005,
                    value=float(cfg(config, "visuals", "loop_zoom_amount", 0.02)),
                )
            with col2:
                visuals["loop_pan_amount"] = st.slider(
                    "Pan amount",
                    min_value=0.0, max_value=0.5, step=0.05,
                    value=float(cfg(config, "visuals", "loop_pan_amount", 0.15)),
                )

            # Effects
            effect_options = ["steam", "sway", "flicker", "color_drift", "vignette"]
            default_effects = cfg(config, "visuals", "loop_effects", ["flicker", "vignette"])
            if isinstance(default_effects, str):
                default_effects = [e.strip() for e in default_effects.split(",") if e.strip()]

            visuals["loop_effects"] = st.multiselect(
                "Effects",
                options=effect_options,
                default=[e for e in default_effects if e in effect_options],
            )

            # Effect-specific settings
            if "steam" in visuals["loop_effects"]:
                with st.expander("Steam Settings"):
                    col1, col2 = st.columns(2)
                    with col1:
                        visuals["loop_steam_opacity"] = st.slider("Opacity", 0.0, 0.2, float(cfg(config, "visuals", "loop_steam_opacity", 0.08)), 0.01)
                        visuals["loop_steam_blur"] = st.slider("Blur", 0.0, 30.0, float(cfg(config, "visuals", "loop_steam_blur", 10.0)), 1.0)
                    with col2:
                        visuals["loop_steam_drift_x"] = st.slider("Drift X", 0.0, 0.1, float(cfg(config, "visuals", "loop_steam_drift_x", 0.02)), 0.005)
                        visuals["loop_steam_drift_y"] = st.slider("Drift Y", 0.0, 0.2, float(cfg(config, "visuals", "loop_steam_drift_y", 0.05)), 0.01)

            if "flicker" in visuals["loop_effects"]:
                visuals["loop_flicker_amount"] = st.slider(
                    "Flicker amount",
                    min_value=0.0, max_value=0.05, step=0.005,
                    value=float(cfg(config, "visuals", "loop_flicker_amount", 0.015)),
                )

            if "vignette" in visuals["loop_effects"]:
                visuals["loop_vignette_angle"] = st.slider(
                    "Vignette strength",
                    min_value=0.2, max_value=1.5, step=0.05,
                    value=safe_float(cfg(config, "visuals", "loop_vignette_angle", 0.63), 0.63),
                )

    st.markdown("---")

    # Text overlay
    st.markdown("### Text Overlay")

    col1, col2 = st.columns([2, 1])
    with col1:
        visuals["overlay_text"] = st.text_input(
            "Overlay text",
            cfg(config, "text_overlay", "text", "") or "",
            placeholder="Leave blank to use auto texts"
        )
    with col2:
        visuals["overlay_auto_mode"] = st.selectbox(
            "Auto mode",
            ["daily", "random"],
            index=0 if cfg(config, "text_overlay", "auto_mode", "daily") == "daily" else 1,
        )

    visuals["overlay_auto_texts"] = st.text_area(
        "Auto texts (one per line)",
        "\n".join(cfg(config, "text_overlay", "auto_texts", [])),
        height=80,
        placeholder="LOCK IN\nFOCUS\nRELAX"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        visuals["overlay_apply_to_video"] = st.checkbox(
            "Burn into video",
            value=bool(cfg(config, "text_overlay", "apply_to_video", True)),
        )
    with col2:
        visuals["overlay_create_thumbnail"] = st.checkbox(
            "Create thumbnail",
            value=bool(cfg(config, "text_overlay", "create_thumbnail", True)),
        )
    with col3:
        visuals["overlay_upload_thumbnail"] = st.checkbox(
            "Upload thumbnail",
            value=bool(cfg(config, "text_overlay", "upload_thumbnail", False)),
        )

    with st.expander("Text Styling"):
        col1, col2, col3 = st.columns(3)
        with col1:
            visuals["font_size"] = st.number_input(
                "Font size",
                min_value=10, max_value=400,
                value=int(cfg(config, "text_overlay", "font_size", 96)),
            )
        with col2:
            visuals["font_color"] = st.text_input(
                "Font color",
                cfg(config, "text_overlay", "font_color", "white"),
            )
        with col3:
            visuals["outline_color"] = st.text_input(
                "Outline color",
                cfg(config, "text_overlay", "outline_color", "black"),
            )
        visuals["outline_width"] = st.number_input(
            "Outline width",
            min_value=0, max_value=20,
            value=int(cfg(config, "text_overlay", "outline_width", 4)),
        )
        visuals["fontfile"] = st.text_input(
            "Font file path (optional)",
            cfg(config, "text_overlay", "fontfile", "") or "",
        )
        visuals["upload_font"] = st.file_uploader(
            "Or upload font file (TTF/OTF)",
            type=["ttf", "otf"],
        )

        position_options = {
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "lower third": ("(w-text_w)/2", "(h-text_h)*0.75"),
            "top": ("(w-text_w)/2", "(h-text_h)*0.15"),
        }
        visuals["text_position"] = st.selectbox(
            "Position",
            ["center", "lower third", "top"],
            index=0,
        )
        visuals["overlay_x"], visuals["overlay_y"] = position_options[visuals["text_position"]]

    return visuals


def render_upload_tab(config: dict[str, Any]) -> dict[str, Any]:
    """Render upload configuration tab"""
    upload = {}

    st.markdown("### YouTube Upload")

    upload["enabled"] = st.checkbox(
        "Enable upload",
        value=bool(cfg(config, "upload", "enabled", True)),
    )

    if upload["enabled"]:
        col1, col2 = st.columns(2)
        with col1:
            upload["privacy_status"] = st.selectbox(
                "Privacy",
                ["public", "unlisted", "private"],
                index=["public", "unlisted", "private"].index(
                    cfg(config, "upload", "privacy_status", "public")
                ),
            )
        with col2:
            upload["category_id"] = st.text_input(
                "Category ID",
                cfg(config, "upload", "category_id", "10"),
                help="10 = Music"
            )

        upload["title_template"] = st.text_input(
            "Title template",
            cfg(config, "upload", "title_template", "Daily Chill Mix - {date}"),
        )

        upload["description_template"] = st.text_area(
            "Description template",
            cfg(config, "upload", "description_template", "Longform ambient mix. Generated daily."),
            height=100,
        )

        upload["tags"] = st.text_input(
            "Tags (comma-separated)",
            ", ".join(cfg(config, "upload", "tags", ["ambient", "chill", "lofi"])),
        )

        # YouTube Authentication
        st.markdown("#### YouTube Account")

        # Try new OAuth flow first
        if credentials_configured():
            token = render_youtube_login()
            if token:
                # Save token for CLI use
                token_path = SECRETS_DIR / "youtube_token.json"
                save_token_to_file(token, token_path)
                upload["token_json"] = str(token_path)
                upload["credentials_json"] = ""  # Not needed with OAuth flow
                upload["youtube_authenticated"] = True
            else:
                upload["youtube_authenticated"] = False
        else:
            # OAuth not configured - show setup instructions
            st.warning("YouTube login not configured.")
            with st.expander("Setup Instructions"):
                st.markdown("""
                **For App Owners:**
                1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
                2. Create an OAuth 2.0 Client ID (Web application)
                3. Add your app URL as authorized redirect URI
                4. Add credentials to Streamlit secrets or `.env` file:
                   - `GOOGLE_CLIENT_ID`
                   - `GOOGLE_CLIENT_SECRET`
                """)
            upload["youtube_authenticated"] = False
            upload["credentials_json"] = ""
            upload["token_json"] = ""

    st.markdown("---")

    # Tracklist
    st.markdown("### Tracklist")

    col1, col2 = st.columns(2)
    with col1:
        upload["tracklist_enabled"] = st.checkbox(
            "Generate timestamps",
            value=bool(cfg(config, "tracklist", "enabled", True)),
        )
    with col2:
        upload["embed_chapters"] = st.checkbox(
            "Embed chapters in MP4",
            value=bool(cfg(config, "tracklist", "embed_chapters", True)),
        )

    upload["append_to_description"] = st.checkbox(
        "Append to description",
        value=bool(cfg(config, "tracklist", "append_to_description", True)),
    )

    st.markdown("---")

    # Video output settings
    st.markdown("### Video Output")

    col1, col2, col3 = st.columns(3)
    with col1:
        upload["resolution"] = st.text_input(
            "Resolution",
            cfg(config, "video", "resolution", "1920x1080"),
        )
    with col2:
        upload["video_bitrate"] = st.text_input(
            "Video bitrate",
            cfg(config, "video", "video_bitrate", "4500k"),
        )
    with col3:
        upload["audio_bitrate"] = st.text_input(
            "Audio bitrate",
            cfg(config, "video", "audio_bitrate", "192k"),
        )

    return upload


def render_settings_tab(config: dict[str, Any]) -> dict[str, Any]:
    """Render settings/schedule tab"""
    settings = {}

    st.markdown("### Project")

    col1, col2 = st.columns(2)
    with col1:
        settings["project_name"] = st.text_input(
            "Project name",
            cfg(config, "project", "name", "daily_chill_mix"),
        )
    with col2:
        settings["output_dir"] = st.text_input(
            "Output folder",
            cfg(config, "project", "output_dir", "runs"),
        )

    st.markdown("---")

    # Schedule
    st.markdown("### Schedule")

    col1, col2 = st.columns(2)
    with col1:
        settings["schedule_enabled"] = st.checkbox(
            "Enable daily schedule",
            value=bool(cfg(config, "schedule", "enabled", True)),
        )
    with col2:
        settings["daily_time"] = st.text_input(
            "Daily time (HH:MM)",
            cfg(config, "schedule", "daily_time", "03:00"),
        )

    st.markdown("---")

    # Test mode
    st.markdown("### Test Mode")

    col1, col2 = st.columns(2)
    with col1:
        settings["test_enabled"] = st.checkbox(
            "Enable test mode",
            value=bool(cfg(config, "test", "enabled", False)),
            help="No upload, no repeat"
        )
    with col2:
        settings["test_max_minutes"] = st.number_input(
            "Max minutes (0 = full)",
            min_value=0, max_value=720,
            value=int(cfg(config, "test", "max_minutes", 0) or 0),
        )

    st.markdown("---")

    # Presets
    st.markdown("### Quick Presets")

    preset_choice = st.selectbox(
        "Load preset",
        ["None"] + sorted(PRESETS.keys()),
    )

    if st.button("Apply Preset"):
        if preset_choice != "None":
            st.session_state.config = apply_preset(
                st.session_state.config,
                PRESETS[preset_choice],
            )
            st.success(f"Applied '{preset_choice}' preset")
            st.rerun()

    return settings


def build_full_config(
    audio: dict[str, Any],
    visuals: dict[str, Any],
    upload: dict[str, Any],
    settings: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build the complete config dict from all tabs"""

    # Handle uploaded files
    saved_image_path = visuals.get("image_path", "")
    if visuals.get("upload_image"):
        saved_image_path = save_uploaded_file(visuals["upload_image"], ASSETS_DIR / "image.png")

    saved_loop_path = visuals.get("loop_video_path", "")
    if visuals.get("upload_loop"):
        saved_loop_path = save_uploaded_file(visuals["upload_loop"], ASSETS_DIR / "loop.mp4")

    saved_font_path = visuals.get("fontfile", "") or ""
    if visuals.get("upload_font"):
        suffix = Path(visuals["upload_font"].name).suffix or ".ttf"
        saved_font_path = save_uploaded_file(
            visuals["upload_font"],
            ASSETS_DIR / f"overlay_font{suffix}",
        )

    saved_audio_folder = audio.get("local_folder", "")
    if audio.get("source") == "local" and audio.get("uploaded_files"):
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_upload_dir = ASSETS_DIR / "audio_uploads" / timestamp
        audio_upload_dir.mkdir(parents=True, exist_ok=True)
        for up in audio["uploaded_files"]:
            filename = Path(up.name).name
            (audio_upload_dir / filename).write_bytes(up.getvalue())
        saved_audio_folder = path_for_config(audio_upload_dir)

    saved_youtube_client = upload.get("credentials_json", "secrets/youtube_client.json")
    if upload.get("upload_youtube_client"):
        saved_youtube_client = save_uploaded_file(
            upload["upload_youtube_client"],
            SECRETS_DIR / "youtube_client.json"
        )

    return {
        "project": {
            "name": settings.get("project_name", "daily_chill_mix"),
            "output_dir": settings.get("output_dir", "runs"),
        },
        "audio": {
            "source": audio.get("source", "local"),
            "drive_folder_id": audio.get("drive_folder_id", ""),
            "local_folder": saved_audio_folder or None,
            "ordering": audio.get("ordering", "name"),
            "repeat_playlist": audio.get("repeat_playlist", True),
            "recursive": audio.get("recursive", False),
            "target_hours_min": float(audio["target_hours_min"]) if audio.get("target_hours_min") else None,
            "target_hours_max": float(audio["target_hours_max"]) if audio.get("target_hours_max") else None,
            "target_minutes_min": int(audio["target_minutes_min"]) if audio.get("target_minutes_min") else None,
            "target_minutes_max": int(audio["target_minutes_max"]) if audio.get("target_minutes_max") else None,
            "concat_codec": "libmp3lame",
            "concat_quality": int(audio.get("concat_quality", 2)),
            "concat_bitrate": audio.get("concat_bitrate") or None,
        },
        "drive": {
            "use_service_account": audio.get("use_service_account", True),
            "service_account_json": audio.get("service_account_json") or None,
            "oauth_client_json": audio.get("oauth_client_json") or None,
            "token_json": audio.get("token_json") or None,
        },
        "visuals": {
            "image_prompt": visuals.get("image_prompt", ""),
            "video_prompt": visuals.get("video_prompt", ""),
            "loop_duration_seconds": int(visuals.get("loop_duration_seconds", 5)),
            "fps": int(visuals.get("fps", 30)),
            "image_path": saved_image_path or None,
            "loop_video_path": saved_loop_path or None,
            "image_provider": visuals.get("image_provider", "openai"),
            "openai_api_key_env": cfg(config, "visuals", "openai_api_key_env", "OPENAI_API_KEY"),
            "openai_model": visuals.get("openai_model", "gpt-image-1"),
            "openai_size": visuals.get("openai_size", "1792x1024"),
            "loop_provider": visuals.get("loop_provider", "ffmpeg"),
            "loop_zoom_amount": float(visuals.get("loop_zoom_amount", 0.02)),
            "loop_pan_amount": float(visuals.get("loop_pan_amount", 0.15)),
            "loop_motion_style": visuals.get("loop_motion_style", "cinematic"),
            "loop_effects": visuals.get("loop_effects", []),
            "loop_flicker_amount": float(visuals.get("loop_flicker_amount", 0.015)),
            "loop_vignette_angle": safe_float(visuals.get("loop_vignette_angle", 0.63), 0.63),
            "loop_steam_opacity": float(visuals.get("loop_steam_opacity", 0.08)),
            "loop_steam_blur": float(visuals.get("loop_steam_blur", 10.0)),
            "loop_steam_noise": int(visuals.get("loop_steam_noise", 12)),
            "loop_steam_drift_x": float(visuals.get("loop_steam_drift_x", 0.02)),
            "loop_steam_drift_y": float(visuals.get("loop_steam_drift_y", 0.05)),
            "auto_background": visuals.get("auto_background", False),
            "background_color": visuals.get("background_color", "black"),
        },
        "text_overlay": {
            "text": visuals.get("overlay_text") or None,
            "auto_texts": split_text_lines(visuals.get("overlay_auto_texts", "")),
            "auto_mode": visuals.get("overlay_auto_mode", "daily"),
            "font_size": int(visuals.get("font_size", 96)),
            "font_color": visuals.get("font_color", "white"),
            "outline_color": visuals.get("outline_color", "black"),
            "outline_width": int(visuals.get("outline_width", 4)),
            "fontfile": saved_font_path or None,
            "x": visuals.get("overlay_x", "(w-text_w)/2"),
            "y": visuals.get("overlay_y", "(h-text_h)/2"),
            "apply_to_video": visuals.get("overlay_apply_to_video", True),
            "create_thumbnail": visuals.get("overlay_create_thumbnail", True),
            "upload_thumbnail": visuals.get("overlay_upload_thumbnail", False),
        },
        "video": {
            "resolution": upload.get("resolution", "1920x1080"),
            "fps": int(visuals.get("fps", 30)),
            "video_bitrate": upload.get("video_bitrate", "4500k"),
            "audio_bitrate": upload.get("audio_bitrate", "192k"),
        },
        "upload": {
            "enabled": upload.get("enabled", True),
            "provider": "youtube",
            "credentials_json": saved_youtube_client,
            "token_json": upload.get("token_json", "secrets/youtube_token.json"),
            "privacy_status": upload.get("privacy_status", "public"),
            "category_id": upload.get("category_id", "10"),
            "title_template": upload.get("title_template", "Daily Chill Mix - {date}"),
            "description_template": upload.get("description_template", ""),
            "tags": split_tags(upload.get("tags", "")),
        },
        "tracklist": {
            "enabled": upload.get("tracklist_enabled", True),
            "filename": "tracklist.txt",
            "append_to_description": upload.get("append_to_description", True),
            "embed_chapters": upload.get("embed_chapters", True),
        },
        "test": {
            "enabled": settings.get("test_enabled", False),
            "max_minutes": int(settings.get("test_max_minutes", 0)) or None,
            "disable_upload": True,
            "repeat_playlist": False,
        },
        "schedule": {
            "enabled": settings.get("schedule_enabled", True),
            "daily_time": settings.get("daily_time", "03:00"),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Video Creator Agent",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Password protection
    if not require_password():
        st.stop()

    # Load config
    if "config" not in st.session_state:
        st.session_state.config = load_config()
    config = st.session_state.config

    # Demo mode
    demo_mode = os.getenv("DEMO_MODE") == "1"

    # Render sidebar and get actions
    actions = render_sidebar(config, demo_mode)

    # Header
    st.markdown("# Video Creator Agent")
    st.caption("Automated pipeline for generating looped visual + audio videos")

    # Main tabs
    tab_dashboard, tab_audio, tab_visuals, tab_upload, tab_settings = st.tabs([
        " Dashboard",
        " Audio",
        " Visuals",
        " Upload",
        " Settings"
    ])

    audio_config = {}
    visuals_config = {}
    upload_config = {}
    settings_config = {}

    with tab_dashboard:
        render_dashboard_tab(config)

    with tab_audio:
        audio_config = render_audio_tab(config)

    with tab_visuals:
        visuals_config = render_visuals_tab(config)

    with tab_upload:
        upload_config = render_upload_tab(config)

    with tab_settings:
        settings_config = render_settings_tab(config)

    # Save button (fixed at bottom)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button(" Save Configuration", disabled=demo_mode, use_container_width=True):
            full_config = build_full_config(
                audio_config, visuals_config, upload_config, settings_config, config
            )
            save_config(full_config)
            st.session_state.config = full_config
            st.success("Configuration saved")

    with col2:
        # Preview thumbnail button
        if st.button(" Preview Thumbnail", use_container_width=True):
            auto_texts = split_text_lines(visuals_config.get("overlay_auto_texts", ""))
            selected_text = select_overlay_text(
                visuals_config.get("overlay_text", ""),
                auto_texts,
                visuals_config.get("overlay_auto_mode", "daily"),
            )
            if not selected_text:
                st.warning("Add overlay text to preview")
            else:
                preview_dir = ROOT / "runs" / "_preview"
                preview_dir.mkdir(parents=True, exist_ok=True)
                preview_text_path = preview_dir / "preview_overlay.txt"
                preview_text_path.write_text(selected_text, encoding="utf-8")

                # Determine preview image
                preview_image_path = None
                if visuals_config.get("upload_image"):
                    suffix = Path(visuals_config["upload_image"].name).suffix or ".png"
                    preview_image_path = preview_dir / f"preview_base{suffix}"
                    preview_image_path.write_bytes(visuals_config["upload_image"].getvalue())
                elif visuals_config.get("image_path"):
                    resolved = resolve_path(visuals_config["image_path"])
                    if resolved.exists():
                        preview_image_path = resolved
                elif visuals_config.get("auto_background"):
                    preview_image_path = preview_dir / "preview_base.png"
                    generate_color_image(
                        preview_image_path,
                        resolution=upload_config.get("resolution", "1920x1080"),
                        color=visuals_config.get("background_color", "black"),
                    )
                if not preview_image_path:
                    st.warning("Preview needs an image path, upload, or auto background.")
                else:
                    font_path = None
                    if visuals_config.get("upload_font"):
                        suffix = Path(visuals_config["upload_font"].name).suffix or ".ttf"
                        font_path = preview_dir / f"preview_font{suffix}"
                        font_path.write_bytes(visuals_config["upload_font"].getvalue())
                    elif visuals_config.get("fontfile"):
                        resolved_font = resolve_path(visuals_config["fontfile"])
                        if resolved_font.exists():
                            font_path = resolved_font
                    if font_path is None:
                        font_path = default_fontfile()

                    drawtext_filter = build_drawtext_filter(
                        textfile=preview_text_path,
                        fontfile=font_path,
                        font_size=int(visuals_config.get("font_size", 96)),
                        font_color=visuals_config.get("font_color", "white"),
                        x=visuals_config.get("overlay_x", "(w-text_w)/2"),
                        y=visuals_config.get("overlay_y", "(h-text_h)/2"),
                        border_color=visuals_config.get("outline_color", "black"),
                        border_width=int(visuals_config.get("outline_width", 4)),
                    )
                    preview_output = preview_dir / "thumbnail_preview.png"
                    try:
                        render_image_with_text(preview_image_path, preview_output, drawtext_filter)
                        st.session_state.preview_path = str(preview_output)
                        st.success(f"Preview: {selected_text}")
                    except RuntimeError as exc:
                        st.error(f"Preview failed: {exc}")

    # Show preview if available
    preview_path = st.session_state.get("preview_path")
    if preview_path and Path(preview_path).exists():
        st.markdown("### Thumbnail Preview")
        st.image(preview_path, use_container_width=True)

    # Handle sidebar actions
    if actions["run_preview"]:
        full_config = build_full_config(
            audio_config, visuals_config, upload_config, settings_config, config
        )
        save_config(full_config)
        with st.spinner("Generating 30-second preview..."):
            # Run with 0.5 minutes (30 seconds) for quick preview
            code, output = run_agent_once_cli(CONFIG_PATH, test_mode=True, test_minutes=1)
        st.session_state.last_run_output = output
        if code == 0:
            # Try to find the output video
            preview_dir = RUNS_UI_DIR
            videos = sorted(preview_dir.glob("**/*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if videos:
                st.success("Preview ready!")
                st.video(str(videos[0]))
            else:
                st.success("Preview completed - check runs folder")
        else:
            st.error("Preview failed")

    if actions["run_test"]:
        full_config = build_full_config(
            audio_config, visuals_config, upload_config, settings_config, config
        )
        save_config(full_config)
        test_minutes = int(settings_config.get("test_max_minutes", 10) or 10)
        with st.spinner("Running test..."):
            code, output = run_agent_once_cli(CONFIG_PATH, test_mode=True, test_minutes=test_minutes)
        st.session_state.last_run_output = output
        if code == 0:
            st.success("Test completed")
        else:
            st.error("Test failed")

    if actions["run_full"]:
        full_config = build_full_config(
            audio_config, visuals_config, upload_config, settings_config, config
        )
        save_config(full_config)
        pid = start_background(
            [sys.executable, "-m", "src.agent", "--config", str(CONFIG_PATH), "--once"],
            FULLRUN_PID_PATH, FULLRUN_LOG_PATH,
        )
        st.success(f"Full run started (PID {pid})")

    if actions["stop_full"]:
        if stop_background(FULLRUN_PID_PATH):
            st.success("Full run stopped")
        else:
            st.info("No running job found")

    if actions["start_schedule"]:
        full_config = build_full_config(
            audio_config, visuals_config, upload_config, settings_config, config
        )
        save_config(full_config)
        pid = start_background(
            [sys.executable, "-m", "src.agent", "--config", str(CONFIG_PATH)],
            SCHEDULE_PID_PATH, SCHEDULE_LOG_PATH,
        )
        st.success(f"Schedule started (PID {pid})")

    if actions["stop_schedule"]:
        if stop_background(SCHEDULE_PID_PATH):
            st.success("Schedule stopped")
        else:
            st.info("No running schedule")

    # Show run output
    run_output = st.session_state.get("last_run_output")
    if run_output:
        with st.expander("Run Output"):
            st.code(run_output, language="text")


if __name__ == "__main__":
    main()
