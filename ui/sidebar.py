from typing import Callable, Optional, Tuple
import customtkinter as ctk

from config.settings import ThemeColors
from utils.i18n import LanguageManager, tr


class Sidebar(ctk.CTkFrame):
    """Navigation sidebar with icon-based menu items.

    Handles page navigation by calling registered callbacks when
    a navigation item is clicked. Maintains active state highlight.
    """

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
        self.configure(width=200)
        self.grid_propagate(False)

        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(25, 30))

        ctk.CTkLabel(title_frame, text="📨", font=ctk.CTkFont(size=28)).pack()
        ctk.CTkLabel(title_frame, text="Twilio CM",
                      font=ctk.CTkFont(size=16, weight="bold"),
                      text_color=ThemeColors.ACCENT).pack(pady=(5, 0))

        separator = ctk.CTkFrame(self, height=2, fg_color=ThemeColors.BORDER)
        separator.pack(fill="x", padx=15, pady=5)

        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for page_id, icon, _ in self.NAV_ITEMS:
            label = tr(page_id)
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}  {label}",
                anchor="w",
                fg_color="transparent",
                text_color=ThemeColors.FG_PRIMARY,
                hover_color=ThemeColors.BG_TERTIARY,
                font=ctk.CTkFont(size=13),
                corner_radius=8,
                height=40,
                command=lambda pid=page_id: self._on_item_click(pid),
            )
            btn.pack(fill="x", pady=2)
            self._nav_buttons[page_id] = btn

        separator2 = ctk.CTkFrame(self, height=2, fg_color=ThemeColors.BORDER)
        separator2.pack(fill="x", padx=15, pady=5)

        lang_frame = ctk.CTkFrame(self, fg_color="transparent")
        lang_frame.pack(fill="x", padx=10, pady=(0, 10))

        current_lang = self._lang_mgr.lang
        lang_text = "🇪🇸 Español" if current_lang == "en" else "🇬🇧 English"
        self.lang_btn = ctk.CTkButton(
            lang_frame,
            text=lang_text,
            anchor="center",
            fg_color=ThemeColors.BG_TERTIARY,
            hover_color=ThemeColors.ACCENT_HOVER,
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            height=35,
            command=self._toggle_language,
        )
        self.lang_btn.pack(fill="x", padx=5)

        self._set_active("dashboard")

    def _on_item_click(self, page_id: str) -> None:
        self._set_active(page_id)
        if self.on_navigate:
            self.on_navigate(page_id)

    def _set_active(self, page_id: str) -> None:
        if self._active_item and self._active_item in self._nav_buttons:
            prev = self._nav_buttons[self._active_item]
            prev.configure(fg_color="transparent", text_color=ThemeColors.FG_PRIMARY)

        if page_id in self._nav_buttons:
            current = self._nav_buttons[page_id]
            current.configure(fg_color=ThemeColors.BG_TERTIARY, text_color=ThemeColors.ACCENT)
            self._active_item = page_id

    def _toggle_language(self) -> None:
        new_lang = "es" if self._lang_mgr.lang == "en" else "en"
        self._lang_mgr.lang = new_lang
        self.lang_btn.configure(
            text="🇪🇸 Español" if new_lang == "en" else "🇬🇧 English"
        )
        if self.on_language_toggle:
            self.on_language_toggle(new_lang)

    def set_active(self, page_id: str) -> None:
        self._set_active(page_id)
