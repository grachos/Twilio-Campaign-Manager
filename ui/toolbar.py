from typing import Optional, Callable, Dict
import customtkinter as ctk

from config.settings import ThemeColors
from utils.i18n import tr


class Toolbar(ctk.CTkFrame):
    """Top toolbar — light, slim, contextual action buttons."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", height=40, **kwargs)
        self._buttons: Dict[str, ctk.CTkButton] = {}
        self._callbacks: Dict[str, Optional[Callable]] = {}
        self.grid_propagate(False)
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(10, weight=1)

        actions = [
            ("import", f"📥 {tr('import')}", ThemeColors.ACCENT),
            ("export", f"📤 {tr('export')}", ThemeColors.ACCENT),
        ]

        col = 0
        for action_id, text, color in actions:
            btn = ctk.CTkButton(
                self, text=text, fg_color=color,
                hover_color=ThemeColors.ACCENT_HOVER,
                text_color="#ffffff",
                font=ctk.CTkFont(size=12), width=90, height=30,
                corner_radius=6,
                command=lambda aid=action_id: self._handle_click(aid),
            )
            btn.grid(row=0, column=col, padx=3, pady=5)
            self._buttons[action_id] = btn
            self._callbacks[action_id] = None
            col += 1

        self._hide_all()

    def _handle_click(self, action_id: str) -> None:
        cb = self._callbacks.get(action_id)
        if cb:
            cb()

    def register_callback(self, action_id: str, callback: Callable) -> None:
        if action_id in self._callbacks:
            self._callbacks[action_id] = callback

    def show_campaign_buttons(self) -> None:
        self._hide_all()
        self._show("import")
        self._show("export")

    def show_template_buttons(self) -> None:
        self._hide_all()
        self._show("export")

    def show_general_buttons(self) -> None:
        self._hide_all()
        self._show("import")
        self._show("export")

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
