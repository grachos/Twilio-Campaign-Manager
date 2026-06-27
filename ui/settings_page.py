import json
from tkinter import filedialog, messagebox
from typing import Dict, Any, Optional
import customtkinter as ctk

from config.settings import ThemeColors
from config.config import ConfigManager
from database.database import DatabaseManager
from services.export_service import ExportService
from utils.logger import AppLogger
from utils.i18n import tr


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=ThemeColors.BG_PRIMARY, **kwargs)
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.export_service = ExportService()
        self.logger = AppLogger()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        header = ctk.CTkLabel(self, text=tr("settings"), font=ctk.CTkFont(size=20, weight="bold"), text_color=ThemeColors.FG_PRIMARY)
        header.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        scroll_frame.grid_columnconfigure(1, weight=1)

        sections = [
            ("twilio", tr("twilio_credentials"), [
                ("TWILIO_ACCOUNT_SID", tr("account_sid"), False),
                ("TWILIO_AUTH_TOKEN", tr("auth_token"), True),
                ("TWILIO_MESSAGING_SERVICE_SID", tr("messaging_service_sid"), False),
            ]),
            ("sender", tr("sender_configuration"), [
                ("DEFAULT_SENDER", tr("default_sender"), False),
                ("STATUS_CALLBACK_URL", tr("status_callback_url"), False),
            ]),
            ("performance", tr("performance"), [
                ("RETRY_ATTEMPTS", tr("retry_attempts"), False),
                ("DELAY_BETWEEN_MSGS", tr("delay_between_messages"), False),
                ("MAX_PARALLEL_WORKERS", tr("max_parallel_workers"), False),
            ]),
            ("appearance", tr("appearance"), [
                ("THEME_MODE", tr("theme_mode"), False),
                ("COLOR_THEME", tr("color_theme"), False),
            ]),
        ]

        self._entries = {}
        row = 0
        for section_id, section_title, fields in sections:
            section_frame = ctk.CTkFrame(scroll_frame, fg_color=ThemeColors.BG_SECONDARY, corner_radius=8)
            section_frame.grid(row=row, column=0, sticky="ew", pady=(0, 15))
            section_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(section_frame, text=section_title, font=ctk.CTkFont(size=14, weight="bold"), text_color=ThemeColors.ACCENT
            ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 10))

            for f_idx, (key, label, is_password) in enumerate(fields):
                r = f_idx + 1
                ctk.CTkLabel(section_frame, text=label, font=ctk.CTkFont(size=12), text_color=ThemeColors.FG_PRIMARY
                ).grid(row=r, column=0, sticky="w", padx=20, pady=5)
                show = "*" if is_password else ""
                entry = ctk.CTkEntry(section_frame, show=show, fg_color=ThemeColors.INPUT_BG)
                entry.grid(row=r, column=1, sticky="ew", padx=(0, 20), pady=5)
                self._entries[key] = entry

            row += 1

        self._build_password_toggle(scroll_frame, row)

        row += 1
        btn_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        btn_frame.grid(row=row, column=0, pady=10)

        ctk.CTkButton(btn_frame, text=tr("test_connection"), fg_color=ThemeColors.INFO, command=self._test_connection, width=130
        ).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text=tr("save_settings"), fg_color=ThemeColors.ACCENT, command=self._save_settings, width=130
        ).grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_frame, text=tr("export_config"), fg_color=ThemeColors.BG_TERTIARY, command=self._export_config, width=130
        ).grid(row=0, column=2, padx=5)
        ctk.CTkButton(btn_frame, text=tr("import_config"), fg_color=ThemeColors.BG_TERTIARY, command=self._import_config, width=130
        ).grid(row=0, column=3, padx=5)
        ctk.CTkButton(btn_frame, text=tr("reset_to_defaults"), fg_color=ThemeColors.DANGER, command=self._reset_defaults, width=130
        ).grid(row=0, column=4, padx=5)

        self._test_result_label = ctk.CTkLabel(scroll_frame, text="", font=ctk.CTkFont(size=12))
        self._test_result_label.grid(row=row + 1, column=0, pady=5)

    def _build_password_toggle(self, parent, row):
        toggle_frame = ctk.CTkFrame(parent, fg_color="transparent")
        toggle_frame.grid(row=row, column=0, sticky="w", padx=20, pady=5)
        self._show_passwords = False

        def toggle():
            self._show_passwords = not self._show_passwords
            show = "" if self._show_passwords else "*"
            for key, entry in self._entries.items():
                if "AUTH_TOKEN" in key:
                    entry.configure(show=show)
            toggle_btn.configure(text=tr("hide_passwords") if self._show_passwords else tr("show_passwords"))

        toggle_btn = ctk.CTkButton(toggle_frame, text=tr("show_passwords"), fg_color=ThemeColors.BG_TERTIARY, command=toggle, width=130)
        toggle_btn.grid(row=0, column=0)

    def _load_settings(self):
        db_settings = self.db.get_all_settings()
        for key, entry in self._entries.items():
            raw = db_settings.get(key.lower(), str(self.config.get(key, "")))
            if raw and ("AUTH_TOKEN" in key or "ACCOUNT_SID" in key):
                try:
                    raw = self.config.decrypt(raw)
                except Exception:
                    raw = self.config.get(key, "")
            entry.delete(0, "end")
            entry.insert(0, str(raw))

    def _save_settings(self):
        for key, entry in self._entries.items():
            value = entry.get().strip()
            self.config.set(key, value)
            if "AUTH_TOKEN" in key or "ACCOUNT_SID" in key:
                encrypted = self.config.encrypt(value)
                self.db.set_setting(key.lower(), encrypted)
            else:
                self.db.set_setting(key.lower(), value)

        self.config.update_from_db(self.db.get_all_settings())
        self.logger.info("Settings saved")
        messagebox.showinfo(tr("saved"), tr("settings_saved_successfully"))

    def _test_connection(self):
        sid = self._entries.get("TWILIO_ACCOUNT_SID", ctk.CTkEntry(self)).get().strip()
        token = self._entries.get("TWILIO_AUTH_TOKEN", ctk.CTkEntry(self)).get().strip()
        if not sid:
            self._test_result_label.configure(text=f"✗ {tr('account_sid_is_empty')}", text_color=ThemeColors.DANGER)
            return
        if not token:
            self._test_result_label.configure(text=f"✗ {tr('auth_token_is_empty')}", text_color=ThemeColors.DANGER)
            return
        if not sid.startswith("AC"):
            self._test_result_label.configure(text=f"✗ {tr('account_sid_should_start_with_ac')}", text_color=ThemeColors.DANGER)
            return
        self.config.set("TWILIO_ACCOUNT_SID", sid)
        self.config.set("TWILIO_AUTH_TOKEN", token)
        from services.twilio_service import TwilioService
        svc = TwilioService()
        svc.reset_client()
        success, msg = svc.test_connection()
        color = ThemeColors.SUCCESS if success else ThemeColors.DANGER
        icon = "✓" if success else "✗"
        self._test_result_label.configure(text=f"{icon} {msg}", text_color=color)
        self.logger.info(f"Connection test: {msg}")

    def _export_config(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[(tr("json"), "*.json")])
        if filepath:
            config_data = {key: entry.get() for key, entry in self._entries.items()}
            config_data["app_version"] = self.config.get("APP_VERSION", "1.0.0")
            try:
                with open(filepath, "w") as f:
                    json.dump(config_data, f, indent=2)
                messagebox.showinfo(tr("exported"), f"{tr('configuration_exported_to')} {filepath}")
            except Exception as e:
                messagebox.showerror(tr("error"), str(e))

    def _import_config(self):
        filepath = filedialog.askopenfilename(filetypes=[(tr("json"), "*.json")])
        if filepath:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                for key, value in data.items():
                    if key in self._entries:
                        self._entries[key].delete(0, "end")
                        self._entries[key].insert(0, str(value))
                messagebox.showinfo(tr("imported"), tr("configuration_loaded_click_save"))
            except Exception as e:
                messagebox.showerror(tr("error"), str(e))

    def _reset_defaults(self):
        if messagebox.askyesno(tr("confirm"), tr("reset_all_settings_to_defaults")):
            self._load_settings()
