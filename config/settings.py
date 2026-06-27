from pathlib import Path
from typing import Dict, Tuple


_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    APP_NAME = "Twilio Campaign Manager"
    APP_VERSION = "1.0.0"
    BASE_DIR = str(_BASE_DIR)
    DB_PATH = str(_BASE_DIR / "campaign_manager.db")
    LOG_DIR = str(_BASE_DIR / "logs")
    CAMPAIGNS_DIR = str(_BASE_DIR / "campaigns")
    TEMPLATES_DIR = str(_BASE_DIR / "templates")
    EXPORTS_DIR = str(_BASE_DIR / "exports")
    ASSETS_DIR = str(_BASE_DIR / "assets")

    RETRY_ATTEMPTS = 3
    DELAY_BETWEEN_MSGS = 0.5
    MAX_PARALLEL_WORKERS = 5
    SOCKET_TIMEOUT = 30
    MAX_RECIPIENTS_PER_BATCH = 10000

    TWILIO_API_VERSION = "2010-04-01"
    TWILIO_MESSAGE_TYPE = "whatsapp"
    WHATSAPP_PREFIX = "whatsapp:"
    SMS_PREFIX = "sms:"

    PHONE_REGEX = r"^\+?1?\d{10,15}$"
    VALID_FILE_EXTENSIONS = (".csv", ".xlsx", ".xls", ".json")
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    EXPORT_DATE_FORMAT = "%Y%m%d_%H%M%S"

    LOG_MAX_BYTES = 5 * 1024 * 1024
    LOG_BACKUP_COUNT = 3
    DASHBOARD_REFRESH_SECONDS = 5
    SUPPORTED_IMPORT_FORMATS = ("csv", "excel", "json", "paste")

    STATUS_LABELS = {
        "queued": "Queued", "sending": "Sending", "sent": "Sent",
        "delivered": "Delivered", "failed": "Failed", "cancelled": "Cancelled",
    }

    STATUS_COLORS = {
        "queued": "#FFA500", "sending": "#1E90FF", "sent": "#32CD32",
        "delivered": "#00FF7F", "failed": "#FF4444", "cancelled": "#808080",
    }

    WINDOW_MIN_WIDTH = 1200
    WINDOW_MIN_HEIGHT = 750
    SIDEBAR_WIDTH = 200
    TOOLBAR_HEIGHT = 50
    STATUSBAR_HEIGHT = 30


class ThemeColors:
    BG_PRIMARY = "#1a1a2e"
    BG_SECONDARY = "#16213e"
    BG_TERTIARY = "#0f3460"
    FG_PRIMARY = "#e8e8e8"
    FG_SECONDARY = "#a0a0b0"
    ACCENT = "#25D366"
    ACCENT_HOVER = "#1da851"
    DANGER = "#e74c3c"
    WARNING = "#f39c12"
    SUCCESS = "#2ecc71"
    INFO = "#3498db"
    BORDER = "#2a2a4a"
    INPUT_BG = "#0d1b2a"
    SIDEBAR_BG = "#0f3460"
    CARD_BG = "#1a1a3e"
    HIGHLIGHT_ROW = "#1a3a5c"
    ERROR_BG = "#3a1a1a"
    SUCCESS_BG = "#1a3a1a"

    CHART_COLORS = (
        "#25D366", "#3498db", "#e74c3c", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22", "#2ecc71",
    )

    SIDEBAR_NAV_ITEMS = (
        ("Dashboard", "📊", "dashboard"),
        ("Campaigns", "📨", "campaigns"),
        ("Templates", "📋", "templates"),
        ("History", "📜", "history"),
        ("Settings", "⚙️", "settings"),
        ("Logs", "📝", "logs"),
    )

    SEND_BUTTON_CONFIG = {
        "start": "▶ Start", "pause": "⏸ Pause",
        "resume": "▶ Resume", "cancel": "⏹ Cancel",
        "retry": "🔄 Retry Failed",
    }

    GRID_COLUMN_WIDTHS = {
        "phone": 180, "status": 100, "default": 150,
    }
