import customtkinter as ctk
from typing import Optional, Dict, Type

from config.settings import ThemeColors, Settings
from config.config import ConfigManager
from ui.sidebar import Sidebar
from ui.toolbar import Toolbar
from ui.campaign_page import CampaignPage
from ui.templates_page import TemplatesPage
from ui.settings_page import SettingsPage
from ui.logs_page import LogsPage
from utils.logger import AppLogger
from utils.i18n import LanguageManager, tr
from database.database import DatabaseManager


class StatusBar(ctk.CTkFrame):
    """Bottom status bar showing connection status, version, and current page."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=ThemeColors.BG_TERTIARY, height=30, **kwargs)
        self.grid_propagate(False)
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure((0, 2), weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            self, text=f"○ {tr('disconnected')}", font=ctk.CTkFont(size=11),
            text_color=ThemeColors.FG_SECONDARY,
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=2, sticky="w")

        self.page_label = ctk.CTkLabel(
            self, text=tr("dashboard"), font=ctk.CTkFont(size=11),
            text_color=ThemeColors.FG_SECONDARY,
        )
        self.page_label.grid(row=0, column=1, padx=10, pady=2)

        self.version_label = ctk.CTkLabel(
            self, text=f"v{Settings.APP_VERSION}", font=ctk.CTkFont(size=10),
            text_color=ThemeColors.FG_SECONDARY,
        )
        self.version_label.grid(row=0, column=2, padx=10, pady=2, sticky="e")

    def set_status(self, text: str, connected: bool = False) -> None:
        icon = "●" if connected else "○"
        color = ThemeColors.SUCCESS if connected else ThemeColors.FG_SECONDARY
        self.status_label.configure(text=f"{icon} {text}", text_color=color)

    def set_page(self, page_name: str) -> None:
        self.page_label.configure(text=page_name)


class MainWindow(ctk.CTk):
    """Root application window.

    Orchestrates the sidebar, toolbar, statusbar, and page views.
    Manages navigation between pages and coordinates global actions.
    """

    def __init__(self) -> None:
        super().__init__()
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.logger = AppLogger()

        self.title(self.config.app_name)
        self.geometry(f"{Settings.WINDOW_MIN_WIDTH}x{Settings.WINDOW_MIN_HEIGHT}")
        self.minsize(Settings.WINDOW_MIN_WIDTH, Settings.WINDOW_MIN_HEIGHT)

        self._configure_theme()
        self._build_layout()
        self._build_pages()
        self._register_callbacks()
        self._load_settings()

        self.logger.info(f"{self.config.app_name} v{self.config.app_version} started")

    def _configure_theme(self) -> None:
        mode = self.config.get("THEME_MODE", "Dark")
        ctk.set_appearance_mode(mode)
        theme = self.config.get("COLOR_THEME", "green")
        ctk.set_default_color_theme(theme)
        self.configure(fg_color=ThemeColors.BG_PRIMARY)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self.sidebar = Sidebar(self, on_navigate=self._navigate_to, on_language_toggle=self._on_language_toggle)
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsw")

        self.toolbar = Toolbar(self)
        self.toolbar.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 0))

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.statusbar = StatusBar(self)
        self.statusbar.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 10))

    def _build_pages(self) -> None:
        self.pages: Dict[str, ctk.CTkFrame] = {}

        self.pages["dashboard"] = ctk.CTkFrame(self.content_frame, fg_color=ThemeColors.BG_PRIMARY)
        self._build_dashboard_page(self.pages["dashboard"])

        self.pages["campaigns"] = CampaignPage(self.content_frame, self.toolbar, self.statusbar)
        self.pages["templates"] = TemplatesPage(self.content_frame, self.toolbar)
        self.pages["history"] = self._build_history_page()
        self.pages["settings"] = SettingsPage(self.content_frame)
        self.pages["logs"] = LogsPage(self.content_frame)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()

        self.pages["dashboard"].grid()

    def _build_dashboard_page(self, parent) -> None:
        parent.grid_columnconfigure((0, 1, 2, 3), weight=1)
        parent.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            parent, text=tr("dashboard_title"), font=ctk.CTkFont(size=22, weight="bold"),
            text_color=ThemeColors.FG_PRIMARY,
        )
        header.grid(row=0, column=0, columnspan=4, sticky="w", padx=20, pady=(20, 15))

        self._dashboard_cards = {}
        card_configs = [
            ("today_campaigns", f"📊 {tr('todays_campaigns')}", "0", ThemeColors.ACCENT),
            ("total_sent", f"✅ {tr('messages_sent')}", "0", ThemeColors.INFO),
            ("total_failures", f"❌ {tr('total_failures')}", "0", ThemeColors.DANGER),
            ("pending", f"⏳ {tr('pending')}", "0", ThemeColors.WARNING),
        ]

        for i, (key, title, value, color) in enumerate(card_configs):
            card = self._create_card(parent, title, value, color)
            card.grid(row=1, column=i, sticky="nsew", padx=10, pady=10)
            self._dashboard_cards[key] = card

        stats_frame = ctk.CTkFrame(parent, fg_color=ThemeColors.BG_SECONDARY)
        stats_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)
        stats_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(stats_frame, text=f"{tr('total_campaigns')}:",
                      font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=20, pady=10)
        self._total_campaigns_label = ctk.CTkLabel(
            stats_frame, text="0", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ThemeColors.ACCENT)
        self._total_campaigns_label.grid(row=0, column=1, sticky="w", padx=5, pady=10)

        ctk.CTkLabel(stats_frame, text=f"{tr('avg_delivery_time')}:",
                      font=ctk.CTkFont(size=13)).grid(row=0, column=2, sticky="w", padx=20, pady=10)
        self._avg_delivery_label = ctk.CTkLabel(
            stats_frame, text="0s", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ThemeColors.ACCENT)
        self._avg_delivery_label.grid(row=0, column=3, sticky="w", padx=5, pady=10)

        self._refresh_dashboard()

    def _create_card(self, parent, title: str, value: str, accent_color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=ThemeColors.CARD_BG, corner_radius=12)
        card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=12),
                      text_color=ThemeColors.FG_SECONDARY).pack(anchor="w")
        value_label = ctk.CTkLabel(inner, text=value,
                                    font=ctk.CTkFont(size=28, weight="bold"),
                                    text_color=accent_color)
        value_label.pack(anchor="w", pady=(5, 0))

        card.value_label = value_label
        return card

    def _build_history_page(self) -> ctk.CTkFrame:
        from ui.campaign_page import CampaignPage as CP
        frame = ctk.CTkFrame(self.content_frame, fg_color=ThemeColors.BG_PRIMARY)
        return CP._build_history_view(CP(frame, self.toolbar, self.statusbar), frame)

    def _refresh_dashboard(self) -> None:
        try:
            from services.campaign_service import CampaignService
            svc = CampaignService()
            stats = svc.get_dashboard_stats()

            if "today_campaigns" in self._dashboard_cards:
                self._dashboard_cards["today_campaigns"].value_label.configure(
                    text=str(stats.get("today_campaigns", 0)))
            if "total_sent" in self._dashboard_cards:
                self._dashboard_cards["total_sent"].value_label.configure(
                    text=str(stats.get("total_messages_sent", 0)))
            if "total_failures" in self._dashboard_cards:
                self._dashboard_cards["total_failures"].value_label.configure(
                    text=str(stats.get("total_failures", 0)))
            if "pending" in self._dashboard_cards:
                self._dashboard_cards["pending"].value_label.configure(
                    text=str(stats.get("pending_messages", 0)))
            if hasattr(self, "_total_campaigns_label"):
                self._total_campaigns_label.configure(text=str(stats.get("total_campaigns", 0)))
            if hasattr(self, "_avg_delivery_label"):
                self._avg_delivery_label.configure(text=f"{stats.get('avg_delivery_seconds', 0)}s")
        except Exception:
            pass
        self.after(5000, self._refresh_dashboard)

    def _register_callbacks(self) -> None:
        self.toolbar.register_callback("new", self._on_new)
        self.toolbar.register_callback("export", self._on_export)

    def _load_settings(self) -> None:
        try:
            db_settings = self.db.get_all_settings()
            self.config.update_from_db(db_settings)
            saved_lang = db_settings.get("language", "es")
            if saved_lang in ("en", "es"):
                from utils.i18n import LanguageManager
                LanguageManager().lang = saved_lang
            if self.config.twilio_credentials_valid:
                self.statusbar.set_status(tr("connected"), connected=True)
            else:
                self.statusbar.set_status(tr("configure_to_connect"))
        except Exception:
            pass

    def _navigate_to(self, page_id: str) -> None:
        for pid, page in self.pages.items():
            page.grid_remove() if page.winfo_viewable() else None

        if page_id in self.pages:
            self.pages[page_id].grid()
            self.pages[page_id].tkraise()

        self.statusbar.set_page(tr(page_id).capitalize())

        if page_id == "campaigns":
            self.toolbar.show_campaign_buttons()
        elif page_id == "templates":
            self.toolbar.show_template_buttons()
        elif page_id == "logs":
            self.toolbar.show_general_buttons()
        else:
            self.toolbar._hide_all()

        self.sidebar.set_active(page_id)

    def _on_language_toggle(self, new_lang: str) -> None:
        self.db.set_setting("language", new_lang)
        self.logger.info(f"Language changed to {new_lang}")
        from tkinter import messagebox
        messagebox.showinfo(tr("info"), tr("restart_required"))

    def _on_new(self) -> None:
        current_page = self.statusbar.page_label.cget("text").lower()
        if current_page == "campaigns" and "campaigns" in self.pages:
            self.pages["campaigns"]._new_campaign()
        elif current_page == "templates" and "templates" in self.pages:
            self.pages["templates"]._new_template()

    def _on_export(self) -> None:
        current = self.statusbar.page_label.cget("text").lower()
        if current == "logs" and "logs" in self.pages:
            self.pages["logs"]._export_logs()

    def on_closing(self) -> None:
        self.logger.info("Application shutting down")
        self.db.close()
        self.destroy()
