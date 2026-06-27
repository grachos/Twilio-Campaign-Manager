"""Twilio Campaign Manager - Entry Point.

Application for sending thousands of personalized SMS/WhatsApp messages
through Twilio Content Templates with a modern dark-mode GUI.
"""

import sys
import os
from pathlib import Path


def ensure_directories() -> None:
    base = Path(__file__).resolve().parent
    dirs = ["logs", "campaigns", "templates", "exports", "assets/icons"]
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)


def main() -> None:
    ensure_directories()

    try:
        from config.config import ConfigManager
        from utils.logger import AppLogger
        from database.database import DatabaseManager

        config = ConfigManager()
        logger = AppLogger(config.log_dir)
        db = DatabaseManager()

        logger.info("Starting Twilio Campaign Manager")

        from ui.main_window import MainWindow

        app = MainWindow()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()

    except ImportError as e:
        from tkinter import messagebox
        messagebox.showerror(
            "Import Error",
            f"Failed to import required modules:\n{e}\n\n"
            "Please ensure all dependencies are installed:\n"
            "pip install -r requirements.txt",
        )
    except Exception as e:
        from tkinter import messagebox
        import traceback
        messagebox.showerror(
            "Application Error",
            f"An unexpected error occurred:\n{e}\n\n{traceback.format_exc()}",
        )


if __name__ == "__main__":
    main()
