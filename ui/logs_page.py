import json
from tkinter import filedialog, messagebox
from typing import Optional, Dict, Any, List
import customtkinter as ctk
import tkinter as tk

from config.settings import ThemeColors
from utils.i18n import tr
from utils.logger import AppLogger
from database.database import DatabaseManager


class LogsPage(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.logger = AppLogger()
        self.db = DatabaseManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    def _build_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text=tr('logs_page.title'), font=ctk.CTkFont(size=22, weight="bold"), text_color=ThemeColors.FG_PRIMARY
        ).grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(btn_frame, text=tr('logs_page.refresh'), fg_color=ThemeColors.FG_SECONDARY, text_color="#ffffff", corner_radius=6, height=30, command=self._refresh_logs, width=90
        ).grid(row=0, column=0, padx=3)
        ctk.CTkButton(btn_frame, text=tr('logs_page.export'), fg_color=ThemeColors.ACCENT, text_color="#ffffff", corner_radius=6, height=30, command=self._export_logs, width=90
        ).grid(row=0, column=1, padx=3)
        ctk.CTkButton(btn_frame, text=tr('logs_page.clear'), fg_color=ThemeColors.DANGER, text_color="#ffffff", corner_radius=6, height=30, command=self._clear_logs, width=90
        ).grid(row=0, column=2, padx=3)

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=0, column=1, sticky="e", padx=4, pady=(4, 8))

        self.filter_var = ctk.StringVar(value="ALL")
        ctk.CTkOptionMenu(filter_frame, variable=self.filter_var, values=["ALL", "INFO", "SUCCESS", "WARNING", "ERROR"],
                          fg_color=ThemeColors.BG_SECONDARY, button_color=ThemeColors.ACCENT,
                          text_color=ThemeColors.FG_PRIMARY, dropdown_fg_color=ThemeColors.BG_SECONDARY,
                          dropdown_text_color=ThemeColors.FG_PRIMARY, dropdown_hover_color=ThemeColors.BG_TERTIARY,
                          command=lambda _: self._refresh_logs()
        ).pack()

        main_frame = ctk.CTkFrame(self, fg_color=ThemeColors.BG_SECONDARY, corner_radius=8,
                                   border_width=1, border_color=ThemeColors.BORDER)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        text_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(text_frame, fg_color=ThemeColors.BG_PRIMARY, font=ctk.CTkFont(size=12, family="Consolas"))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scroll_btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        scroll_btn_frame.grid(row=0, column=1, sticky="ns", padx=(0, 10))

        def scroll_up():
            self.log_text.yview_scroll(-1, "units")

        def scroll_down():
            self.log_text.yview_scroll(1, "units")

        ctk.CTkButton(scroll_btn_frame, text="▲", width=28, height=22, fg_color=ThemeColors.BG_TERTIARY, text_color=ThemeColors.FG_SECONDARY, corner_radius=4, command=scroll_up
        ).pack(pady=2)
        ctk.CTkButton(scroll_btn_frame, text="▼", width=28, height=22, fg_color=ThemeColors.BG_TERTIARY, text_color=ThemeColors.FG_SECONDARY, corner_radius=4, command=scroll_down
        ).pack(pady=2)

        self.logger.register_callback(self._on_log_entry)
        self._refresh_logs()

    def _on_log_entry(self, entry: Dict[str, Any]):
        self.after(0, self._append_log, entry)

    def _append_log(self, entry: Dict[str, Any]):
        level_filter = self.filter_var.get()
        if level_filter != "ALL" and entry["level"] != level_filter:
            return
        tag = entry["level"]
        formatted = f"{entry['timestamp']} [{entry['level']}] {entry['message']}\n"
        self.log_text.insert("end", formatted)
        self.log_text.see("end")

    def _refresh_logs(self):
        self.log_text.delete("1.0", "end")
        entries = self.logger.get_buffer()
        level_filter = self.filter_var.get()
        for entry in entries:
            if level_filter == "ALL" or entry["level"] == level_filter:
                formatted = f"{entry['timestamp']} [{entry['level']}] {entry['message']}\n"
                self.log_text.insert("end", formatted)
        self.log_text.see("end")

    def _export_logs(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt"), ("CSV", "*.csv")])
        if filepath:
            try:
                content = self.logger.export_buffer()
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo(tr('logs_page.exported_title'), f"{tr('logs_page.exported_message')} {filepath}")
            except Exception as e:
                messagebox.showerror(tr("logs_page.error_title"), str(e))

    def _clear_logs(self):
        if messagebox.askyesno(tr("logs_page.confirm_title"), tr("logs_page.clear_confirm")):
            self.logger.clear_buffer()
            self.log_text.delete("1.0", "end")

    def _export_logs_button(self):
        self._export_logs()

    def destroy(self):
        self.logger.unregister_callback(self._on_log_entry)
        super().destroy()

