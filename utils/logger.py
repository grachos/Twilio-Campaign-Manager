import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any


class AppLogger:
    """Application-wide logging system.

    Provides both file-based logging with rotation and an in-memory
    buffer for UI console display. Supports color-coded log levels
    and callbacks for real-time UI updates.
    """

    _instance: Optional["AppLogger"] = None
    _buffer: List[Dict[str, Any]] = []
    _callbacks: List[Callable] = []
    _buffer_max: int = 10000

    LEVEL_COLORS = {
        "DEBUG": "#808080",
        "INFO": "#25D366",
        "WARNING": "#FFA500",
        "ERROR": "#FF4444",
        "CRITICAL": "#FF0000",
        "SUCCESS": "#00FF7F",
    }

    def __new__(cls, log_dir: str = "logs") -> "AppLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = "logs") -> None:
        if self._initialized:
            return
        self._initialized = True
        self._log_dir = log_dir
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        self._setup_logger()

    def _setup_logger(self) -> None:
        self.logger = logging.getLogger("TwilioCampaignManager")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        log_file = os.path.join(self._log_dir, "campaign_manager.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        error_log = os.path.join(self._log_dir, "errors.log")
        error_handler = RotatingFileHandler(
            error_log, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)

    def _add_to_buffer(self, level: str, message: str, **kwargs) -> None:
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message,
            "color": self.LEVEL_COLORS.get(level, "#FFFFFF"),
            **kwargs,
        }
        self._buffer.append(entry)
        if len(self._buffer) > self._buffer_max:
            self._buffer = self._buffer[-self._buffer_max:]

        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception:
                pass

    def info(self, message: str, **kwargs) -> None:
        self.logger.info(message)
        self._add_to_buffer("INFO", message, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        self.logger.info(f"[SUCCESS] {message}")
        self._add_to_buffer("SUCCESS", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self.logger.warning(message)
        self._add_to_buffer("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self.logger.error(message)
        self._add_to_buffer("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self.logger.critical(message)
        self._add_to_buffer("CRITICAL", message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        self.logger.debug(message)
        self._add_to_buffer("DEBUG", message, **kwargs)

    def register_callback(self, callback: Callable) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_buffer(self, level_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if level_filter:
            return [e for e in self._buffer if e["level"] == level_filter]
        return list(self._buffer)

    def clear_buffer(self) -> None:
        self._buffer.clear()

    def export_buffer(self) -> str:
        lines = []
        for e in self._buffer:
            lines.append(f"{e['timestamp']} [{e['level']}] {e['message']}")
        return "\n".join(lines)

    @property
    def log_file_path(self) -> str:
        return os.path.join(self._log_dir, "campaign_manager.log")
