from typing import Optional, Callable, Dict
import customtkinter as ctk

from config.settings import ThemeColors
from utils.i18n import tr


class Toolbar(ctk.CTkFrame):
    """Top toolbar with action buttons that change contextually.

    Provides Start, Pause/Resume, Cancel, Retry Failed buttons
    for campaigns, plus general actions like New and Export.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=ThemeColors.BG_SECONDARY, height=50, **kwargs)
        self._buttons: Dict[str, ctk.CTkButton] = {}
        self._callbacks: Dict[str, Optional[Callable]] = {}
        self.grid_propagate(False)
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(10, weight=1)

        actions = [
            ("new", f"➕ {tr('new')}", ThemeColors.ACCENT, self._handle_click),
            ("start", f"▶ {tr('start')}", ThemeColors.SUCCESS, self._handle_click),
            ("pause", f"⏸ {tr('pause')}", ThemeColors.WARNING, self._handle_click),
            ("cancel", f"⏹ {tr('cancel')}", ThemeColors.DANGER, self._handle_click),
            ("retry", f"🔄 {tr('retry')}", ThemeColors.INFO, self._handle_click),
            ("export", f"📤 {tr('export')}", ThemeColors.BG_TERTIARY, self._handle_click),
            ("import", f"📥 {tr('import')}", ThemeColors.BG_TERTIARY, self._handle_click),
        ]

        col = 0
        for action_id, text, color, cmd in actions:
            btn = ctk.CTkButton(
                self, text=text, fg_color=color,
                hover_color=self._darken(color),
                font=ctk.CTkFont(size=12), width=100, height=32,
                corner_radius=6,
                command=lambda aid=action_id: self._handle_click(aid),
            )
            btn.grid(row=0, column=col, padx=4, pady=8)
            self._buttons[action_id] = btn
            self._callbacks[action_id] = None
            col += 1

        self._hide_all()

    def _darken(self, color: str) -> str:
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return f"#{max(0, r - 30):02x}{max(0, g - 30):02x}{max(0, b - 30):02x}"
        except (ValueError, IndexError):
            return color

    def _handle_click(self, action_id: str) -> None:
        cb = self._callbacks.get(action_id)
        if cb:
            cb()

    def register_callback(self, action_id: str, callback: Callable) -> None:
        if action_id in self._callbacks:
            self._callbacks[action_id] = callback

    def show_campaign_buttons(self) -> None:
        self._hide_all()
        self._show("new")
        self._show("start")
        self._show("pause")
        self._show("cancel")
        self._show("retry")
        self._show("export")

    def show_template_buttons(self) -> None:
        self._hide_all()
        self._show("new")
        self._show("export")

    def show_general_buttons(self) -> None:
        self._hide_all()
        self._show("new")
        self._show("import")
        self._show("export")

    def show_sending_buttons(self) -> None:
        self._hide_all()
        self._show("pause")
        self._show("cancel")

    def _show(self, action_id: str) -> None:
        if action_id in self._buttons:
            self._buttons[action_id].grid()

    def _hide(self, action_id: str) -> None:
        if action_id in self._buttons:
            self._buttons[action_id].grid_remove()

    def _hide_all(self) -> None:
        for btn in self._buttons.values():
            btn.grid_remove()

    def set_button_state(self, action_id: str, state: str) -> None:
        if action_id in self._buttons:
            self._buttons[action_id].configure(state=state)

    def update_button_text(self, action_id: str, text: str) -> None:
        if action_id in self._buttons:
            self._buttons[action_id].configure(text=text)

    def set_sending_state(self, is_sending: bool) -> None:
        self._hide_all()
        if is_sending:
            self._show("pause")
            self._show("cancel")
        else:
            self.show_campaign_buttons()
