from typing import Callable, Optional, Tuple
import customtkinter as ctk

from config.settings import ThemeColors
from utils.i18n import LanguageManager, tr


class Sidebar(ctk.CTkFrame):
    """Navigation sidebar — dark, compact, web-style."""

    NAV_ITEMS: Tuple[Tuple[str, str, str], ...] = (
        ("dashboard", "📊", "dashboard"),
        ("campaigns", "📨", "campaigns"),
        ("templates", "📋", "templates"),
        ("history", "📜", "history"),
        ("settings", "⚙️", "settings"),
        ("logs", "📝", "logs"),
    )

    def __init__(self, parent, on_navigate: Optional[Callable] = None, on_language_toggle: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color=ThemeColors.SIDEBAR_BG, **kwargs)
        self.on_navigate = on_navigate
        self.on_language_toggle = on_language_toggle
        self._active_item: Optional[str] = None
        self._nav_buttons: dict = {}
        self._lang_mgr = LanguageManager()
        self._build_ui()

    def _build_ui(self) -> None:
        self.configure(width=220)
        self.grid_propagate(False)

        # Logo / brand
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=18, pady=(28, 20))

        ctk.CTkLabel(logo_frame, text="📨", font=ctk.CTkFont(size=26)).pack()
        ctk.CTkLabel(logo_frame, text=tr("app_name"),
                      font=ctk.CTkFont(size=14, weight="bold"),
                      text_color=ThemeColors.SIDEBAR_TEXT).pack(pady=(4, 0))

        sep = ctk.CTkFrame(self, height=1, fg_color="#1e293b")
        sep.pack(fill="x", padx=16, pady=4)

        # Navigation
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="both", expand=True, padx=12, pady=12)

        for page_id, icon, _ in self.NAV_ITEMS:
            label = tr(page_id)
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}  {label}",
                anchor="w",
                fg_color="transparent",
                text_color=ThemeColors.SIDEBAR_TEXT,
                hover_color=ThemeColors.SIDEBAR_HOVER,
                font=ctk.CTkFont(size=13),
                corner_radius=8,
                height=38,
                command=lambda pid=page_id: self._on_item_click(pid),
            )
            btn.pack(fill="x", pady=1)
            self._nav_buttons[page_id] = btn

        # Bottom: language toggle
        sep2 = ctk.CTkFrame(self, height=1, fg_color="#1e293b")
        sep2.pack(fill="x", padx=16, pady=4)

        lang_frame = ctk.CTkFrame(self, fg_color="transparent")
        lang_frame.pack(fill="x", padx=14, pady=(6, 14))

        current_lang = self._lang_mgr.lang
        lang_text = "🇪🇸  Español" if current_lang == "en" else "🇬🇧  English"
        self.lang_btn = ctk.CTkButton(
            lang_frame,
            text=lang_text,
            anchor="center",
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=11),
            corner_radius=6,
            height=32,
            command=self._toggle_language,
        )
        self.lang_btn.pack(fill="x")

        self._set_active("dashboard")

    def _on_item_click(self, page_id: str) -> None:
        self._set_active(page_id)
        if self.on_navigate:
            self.on_navigate(page_id)

    def _set_active(self, page_id: str) -> None:
        if self._active_item and self._active_item in self._nav_buttons:
            prev = self._nav_buttons[self._active_item]
            prev.configure(fg_color="transparent", text_color=ThemeColors.SIDEBAR_TEXT)

        if page_id in self._nav_buttons:
            current = self._nav_buttons[page_id]
            current.configure(fg_color="#1e293b", text_color=ThemeColors.SIDEBAR_ACTIVE)
            self._active_item = page_id

    def _toggle_language(self) -> None:
        new_lang = "es" if self._lang_mgr.lang == "en" else "en"
        self._lang_mgr.lang = new_lang
        self.lang_btn.configure(
            text="🇪🇸  Español" if new_lang == "en" else "🇬🇧  English"
        )
        if self.on_language_toggle:
            self.on_language_toggle(new_lang)

    def set_active(self, page_id: str) -> None:
        self._set_active(page_id)
