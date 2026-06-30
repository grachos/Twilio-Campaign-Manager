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
    BG_PRIMARY = "#f8fafc"
    BG_SECONDARY = "#ffffff"
    BG_TERTIARY = "#f1f5f9"
    FG_PRIMARY = "#1e293b"
    FG_SECONDARY = "#64748b"
    ACCENT = "#3b82f6"
    ACCENT_HOVER = "#2563eb"
    DANGER = "#ef4444"
    WARNING = "#f59e0b"
    SUCCESS = "#10b981"
    INFO = "#3b82f6"
    BORDER = "#e2e8f0"
    INPUT_BG = "#ffffff"
    SIDEBAR_BG = "#0f172a"
    CARD_BG = "#ffffff"
    HIGHLIGHT_ROW = "#eff6ff"
    ERROR_BG = "#fef2f2"
    SUCCESS_BG = "#f0fdf4"

    SIDEBAR_TEXT = "#f8fafc"
    SIDEBAR_HOVER = "#1e293b"
    SIDEBAR_ACTIVE = "#3b82f6"

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
