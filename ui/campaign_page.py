import json
import threading
import time
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Any, Tuple
import customtkinter as ctk
import tkinter as tk

from config.settings import ThemeColors
from config.config import ConfigManager
from database.database import DatabaseManager
from database.models import Campaign
from services.campaign_service import CampaignService
from services.template_service import TemplateService
from services.import_service import ImportService
from services.export_service import ExportService
from services.twilio_service import TwilioService
from workers.sender_worker import SenderWorker
from utils.logger import AppLogger
from utils.validators import Validators
from utils.i18n import tr
from ui.dialogs import CampaignDialog, ImportDialog, SelectColumnsDialog, DataPreviewDialog


class CampaignPage(ctk.CTkFrame):
    """Main campaign management page — light web style."""

    def __init__(self, parent, toolbar, statusbar, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.toolbar = toolbar
        self.statusbar = statusbar
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.logger = AppLogger()
        self.campaign_service = CampaignService()
        self.template_service = TemplateService()
        self.import_service = ImportService()
        self.export_service = ExportService()
        self.sender_worker = SenderWorker()

        self._current_campaign: Optional[Dict] = None
        self._imported_data: List[Dict] = []
        self._imported_columns: List[str] = []
        self._column_mapping: Dict[str, str] = {}
        self._selected_template: Optional[Dict] = None
        self._is_sending = False
        self._send_thread: Optional[threading.Thread] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=0)

        self._build_ui()
        self._register_worker_callbacks()

    def _build_ui(self) -> None:
        # Header and campaign selector
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        header_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(header_frame, text=tr("campaigns"),
                      font=ctk.CTkFont(size=22, weight="bold"),
                      text_color=ThemeColors.FG_PRIMARY).grid(row=0, column=0, padx=4)

        self.campaign_selector = ctk.CTkOptionMenu(
            header_frame, values=[f"✨ {tr('new_campaign')}..."],
            fg_color=ThemeColors.BG_SECONDARY, button_color=ThemeColors.ACCENT,
            text_color=ThemeColors.FG_PRIMARY, dropdown_fg_color=ThemeColors.BG_SECONDARY,
            dropdown_text_color=ThemeColors.FG_PRIMARY, dropdown_hover_color=ThemeColors.BG_TERTIARY,
            command=self._on_campaign_selected,
        )
        self.campaign_selector.grid(row=0, column=1, padx=10)

        ctk.CTkButton(header_frame, text=f"➕ {tr('new_campaign')}",
                       fg_color=ThemeColors.ACCENT, hover_color=ThemeColors.ACCENT_HOVER,
                       text_color="#ffffff", corner_radius=6, height=32,
                       command=self._new_campaign).grid(row=0, column=3, padx=4)
        self._edit_btn = ctk.CTkButton(header_frame, text=f"✏ {tr('edit')}",
                                        fg_color=ThemeColors.FG_SECONDARY,
                                        text_color="#ffffff", corner_radius=6, height=32,
                                        state="disabled", command=self._edit_campaign)
        self._edit_btn.grid(row=0, column=4, padx=4)
        ctk.CTkButton(header_frame, text=f"🗑 {tr('clear_all')}",
                       fg_color=ThemeColors.DANGER, text_color="#ffffff", corner_radius=6, height=32,
                       command=self._clear_all_campaigns).grid(row=0, column=5, padx=4)

        # Campaign info bar
        self.info_bar = ctk.CTkFrame(self, fg_color=ThemeColors.BG_SECONDARY,
                                      corner_radius=8, border_width=1, border_color=ThemeColors.BORDER)
        self.info_bar.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        self.info_bar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self._info_labels = {}
        for i, (key, text) in enumerate([
            ("template", f"{tr('template')}: —"),
            ("recipients", f"{tr('recipients')}: 0"),
            ("sent", f"{tr('sent')}: 0"),
            ("failed", f"{tr('failed')}: 0"),
            ("status", f"{tr('status')}: draft"),
        ]):
            lbl = ctk.CTkLabel(self.info_bar, text=text, font=ctk.CTkFont(size=12),
                                text_color=ThemeColors.FG_SECONDARY)
            lbl.grid(row=0, column=i, padx=10, pady=8)
            self._info_labels[key] = lbl

        # Main content area with notebook tabs
        self.notebook = ctk.CTkTabview(self, fg_color=ThemeColors.BG_SECONDARY,
                                       border_width=1, border_color=ThemeColors.BORDER)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

        self.recipients_tab = self.notebook.add(tr("recipients"))
        self.preview_tab = self.notebook.add(tr("preview"))
        self.results_tab = self.notebook.add(tr("results"))

        self._build_recipients_tab()
        self._build_preview_tab()
        self._build_results_tab()

        # Progress section
        progress_frame = ctk.CTkFrame(self, fg_color=ThemeColors.BG_SECONDARY, corner_radius=8,
                                       border_width=1, border_color=ThemeColors.BORDER)
        progress_frame.grid(row=3, column=0, sticky="ew", padx=4, pady=4)
        progress_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(progress_frame, text=f"{tr('progress')}:",
                      font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=10, pady=6)
        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=300,
                                                fg_color=ThemeColors.BG_TERTIARY,
                                                progress_color=ThemeColors.ACCENT)
        self.progress_bar.grid(row=0, column=1, padx=10, pady=6)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(progress_frame, text="0 / 0",
                                            font=ctk.CTkFont(size=12))
        self.progress_label.grid(row=0, column=2, padx=5, pady=6)

        self.stats_label = ctk.CTkLabel(progress_frame, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color=ThemeColors.FG_SECONDARY)
        self.stats_label.grid(row=0, column=3, padx=10, pady=6)

        # Send buttons
        send_frame = ctk.CTkFrame(self, fg_color="transparent")
        send_frame.grid(row=4, column=0, pady=(4, 8))

        self.start_btn = ctk.CTkButton(send_frame, text=f"▶ {tr('start_sending')}",
                                        fg_color=ThemeColors.ACCENT, hover_color=ThemeColors.ACCENT_HOVER,
                                        text_color="#ffffff", corner_radius=6, width=140, height=34,
                                        state="disabled", command=self._start_sending)
        self.start_btn.grid(row=0, column=0, padx=4)

        self.pause_btn = ctk.CTkButton(send_frame, text=f"⏸ {tr('pause')}",
                                        fg_color=ThemeColors.WARNING, text_color="#ffffff",
                                        corner_radius=6, width=100, height=34,
                                        state="disabled", command=self._toggle_pause)
        self.pause_btn.grid(row=0, column=1, padx=4)

        self.cancel_btn = ctk.CTkButton(send_frame, text=f"⏹ {tr('cancel')}",
                                         fg_color=ThemeColors.DANGER, text_color="#ffffff",
                                         corner_radius=6, width=100, height=34,
                                         state="disabled", command=self._cancel_sending)
        self.cancel_btn.grid(row=0, column=2, padx=4)

        self.retry_btn = ctk.CTkButton(send_frame, text=f"🔄 {tr('retry_failed')}",
                                        fg_color=ThemeColors.ACCENT, text_color="#ffffff",
                                        corner_radius=6, width=120, height=34,
                                        state="disabled", command=self._retry_failed)
        self.retry_btn.grid(row=0, column=3, padx=4)

        self._refresh_campaign_list()

    def _build_recipients_tab(self) -> None:
        self.recipients_tab.grid_columnconfigure(0, weight=1)
        self.recipients_tab.grid_rowconfigure(1, weight=1)

        btn_frame = ctk.CTkFrame(self.recipients_tab, fg_color="transparent")
        btn_frame.grid(row=0, column=0, sticky="ew", pady=5)
        btn_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        ctk.CTkButton(btn_frame, text=f"📂 {tr('import_file')}", command=self._import_file,
                       fg_color=ThemeColors.ACCENT, text_color="#ffffff", corner_radius=6, height=30,
                       hover_color=ThemeColors.ACCENT_HOVER).grid(row=0, column=0, padx=3)
        ctk.CTkButton(btn_frame, text=f"📋 {tr('paste')}", command=self._import_paste,
                       fg_color=ThemeColors.ACCENT, text_color="#ffffff", corner_radius=6, height=30,
                       hover_color=ThemeColors.ACCENT_HOVER).grid(row=0, column=1, padx=3)
        ctk.CTkButton(btn_frame, text=f"🗺 {tr('map_columns')}", command=self._map_columns,
                       fg_color=ThemeColors.FG_SECONDARY, text_color="#ffffff", corner_radius=6, height=30).grid(row=0, column=2, padx=3)
        ctk.CTkButton(btn_frame, text=f"🔍 {tr('search')}", command=self._search_grid,
                       fg_color=ThemeColors.FG_SECONDARY, text_color="#ffffff", corner_radius=6, height=30).grid(row=0, column=3, padx=3)
        ctk.CTkButton(btn_frame, text=f"🗑 {tr('delete_row')}", command=self._delete_selected,
                       fg_color=ThemeColors.DANGER, text_color="#ffffff", corner_radius=6, height=30).grid(row=0, column=4, padx=3)
        ctk.CTkButton(btn_frame, text=f"📊 {tr('preview_data')}", command=self._preview_data,
                       fg_color=ThemeColors.FG_SECONDARY, text_color="#ffffff", corner_radius=6, height=30).grid(row=0, column=5, padx=3)

        tree_frame = ctk.CTkFrame(self.recipients_tab, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, show="headings", height=12)
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.records_count = ctk.CTkLabel(self.recipients_tab, text=f"0 {tr('records')}",
                                           font=ctk.CTkFont(size=11))
        self.records_count.grid(row=2, column=0, sticky="w", pady=2)

    def _build_preview_tab(self) -> None:
        self.preview_tab.grid_columnconfigure(0, weight=1)
        self.preview_tab.grid_rowconfigure(0, weight=1)

        self.preview_text = ctk.CTkTextbox(self.preview_tab, font=ctk.CTkFont(size=13),
                                            fg_color=ThemeColors.BG_PRIMARY,
                                            text_color=ThemeColors.FG_PRIMARY)
        self.preview_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.preview_text.insert("1.0", tr("select_campaign_preview"))
        self.preview_text.configure(state="disabled")

    def _build_results_tab(self) -> None:
        self.results_tab.grid_columnconfigure(0, weight=1)
        self.results_tab.grid_rowconfigure(1, weight=1)

        btn_frame = ctk.CTkFrame(self.results_tab, fg_color="transparent")
        btn_frame.grid(row=0, column=0, sticky="ew", pady=(5, 0))
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(btn_frame, text=f"🔄 {tr('refresh_status')}", command=self._check_delivery_status,
                       fg_color=ThemeColors.ACCENT, text_color="#ffffff", corner_radius=6, height=30).grid(row=0, column=0, padx=3)
        ctk.CTkButton(btn_frame, text=f"📤 {tr('export')}", command=self._export_results,
                       fg_color=ThemeColors.FG_SECONDARY, text_color="#ffffff", corner_radius=6, height=30).grid(row=0, column=1, padx=3)

        results_frame = ctk.CTkFrame(self.results_tab, fg_color="transparent")
        results_frame.grid(row=1, column=0, sticky="nsew")
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        self.results_tree = ttk.Treeview(results_frame, show="headings", height=12)
        self.results_tree.grid(row=0, column=0, sticky="nsew")

        rvsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        rhsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=rvsb.set, xscrollcommand=rhsb.set)
        rvsb.grid(row=0, column=1, sticky="ns")
        rhsb.grid(row=1, column=0, sticky="ew")

        self.results_count = ctk.CTkLabel(self.results_tab, text=f"0 {tr('records')}",
                                           font=ctk.CTkFont(size=11))
        self.results_count.grid(row=2, column=0, sticky="w", pady=2)

    def _register_worker_callbacks(self) -> None:
        self.sender_worker.register_progress_callback(self._on_progress_update)
        self.sender_worker.register_log_callback(self._on_worker_log)
        self.sender_worker.register_complete_callback(self._on_send_complete)

    def _refresh_campaign_list(self) -> None:
        campaigns = self.campaign_service.get_all_campaigns()
        names = [c.name for c in campaigns]
        self.campaign_selector.configure(values=[tr("new_campaign") + "..."] + names)
        if self._current_campaign:
            self.campaign_selector.set(self._current_campaign.get("name", "New Campaign..."))

    def _on_campaign_selected(self, selection: str) -> None:
        if selection == tr("new_campaign") + "...":
            self._new_campaign()
            return

        campaigns = self.campaign_service.get_all_campaigns()
        for c in campaigns:
            if c.name == selection:
                self._load_campaign(c.id)
                break

    def _load_campaign(self, campaign_id: int) -> None:
        campaign = self.campaign_service.get_campaign(campaign_id)
        if not campaign:
            return

        self._current_campaign = {
            "id": campaign.id,
            "name": campaign.name,
            "description": campaign.description,
            "template_id": campaign.template_id,
            "template_name": campaign.template_name,
            "status": campaign.status,
        }

        self.campaign_selector.set(campaign.name)
        self._edit_btn.configure(state="normal")
        self._update_info_bar()

        results = self.campaign_service.get_campaign_results(campaign_id)
        self._imported_data = []
        for r in results:
            vars_dict = r.variables_used if r.variables_used else {}
            row = {"phone": r.phone, "status": r.status, "id": r.id}
            row.update(vars_dict)
            self._imported_data.append(row)

        if results:
            self._imported_columns = list(results[0].variables_used.keys()) if results[0].variables_used else []
        self._populate_grid()
        self._update_preview()
        self._update_send_button_state()

    def _new_campaign(self) -> None:
        templates = self.template_service.get_template_names()
        from ui.dialogs import CampaignDialog
        dialog = CampaignDialog(self.master.master if hasattr(self.master, "master") else self, templates)
        self.wait_window(dialog)

        if dialog.result:
            tmpl = None
            tmpl_name = dialog.result.get("template_name", "")
            if tmpl_name and tmpl_name != "No templates available":
                all_templates = self.template_service.get_all_templates()
                for t in all_templates:
                    if t.name == tmpl_name:
                        tmpl = t
                        break

            campaign_id = self.campaign_service.create_campaign(
                name=dialog.result["name"],
                description=dialog.result.get("description", ""),
                template_id=tmpl.id if tmpl else 0,
                template_name=tmpl.name if tmpl else "",
            )

            self._current_campaign = {
                "id": campaign_id,
                "name": dialog.result["name"],
                "description": dialog.result.get("description", ""),
                "template_id": tmpl.id if tmpl else 0,
                "template_name": tmpl.name if tmpl else "",
                "status": "draft",
            }

            if tmpl:
                self._selected_template = tmpl.to_dict() if hasattr(tmpl, 'to_dict') else tmpl

            self._edit_btn.configure(state="normal")
            self._refresh_campaign_list()
            self._update_info_bar()
            self._update_preview()
            self._update_send_button_state()
            self.logger.info(f"Campaign created: {dialog.result['name']}")

    def _edit_campaign(self) -> None:
        camp = self._current_campaign
        if not camp:
            return
        templates = self.template_service.get_template_names()
        from ui.dialogs import CampaignDialog
        dialog = CampaignDialog(self.master.master if hasattr(self.master, "master") else self,
                                templates, campaign_data=camp)
        self.wait_window(dialog)

        if dialog.result:
            tmpl = None
            tmpl_name = dialog.result.get("template_name", "")
            if tmpl_name and tmpl_name != "No templates available":
                all_templates = self.template_service.get_all_templates()
                for t in all_templates:
                    if t.name == tmpl_name:
                        tmpl = t
                        break

            new_template_id = tmpl.id if tmpl else camp.get("template_id", 0)
            new_template_name = tmpl.name if tmpl else camp.get("template_name", "")

            self.campaign_service.update_campaign(
                camp["id"],
                name=dialog.result["name"],
                description=dialog.result.get("description", ""),
                template_id=new_template_id,
                template_name=new_template_name,
            )

            self._current_campaign.update(
                name=dialog.result["name"],
                description=dialog.result.get("description", ""),
                template_id=new_template_id,
                template_name=new_template_name,
            )

            self._refresh_campaign_list()
            self._update_info_bar()
            self._update_preview()
            self._update_send_button_state()
            self.logger.info(f"Campaign updated: {dialog.result['name']}")

    def _update_info_bar(self) -> None:
        if not self._current_campaign:
            return
        stats = {}
        if self._current_campaign.get("id"):
            stats = self.campaign_service.get_results_stats(self._current_campaign["id"])

        self._info_labels["template"].configure(
            text=f"{tr('template')}: {self._current_campaign.get('template_name', '—')}")
        self._info_labels["recipients"].configure(
            text=f"{tr('recipients')}: {stats.get('total', 0)}")
        self._info_labels["sent"].configure(
            text=f"{tr('sent')}: {stats.get('sent', 0) + stats.get('delivered', 0)}")
        self._info_labels["failed"].configure(
            text=f"{tr('failed')}: {stats.get('failed', 0)}")
        self._info_labels["status"].configure(
            text=f"{tr('status')}: {self._current_campaign.get('status', 'draft')}")

    def _update_send_button_state(self) -> None:
        has_data = len(self._imported_data) > 0
        has_campaign = self._current_campaign is not None
        has_template = has_campaign and bool(self._current_campaign.get("template_id"))
        not_sending = not self._is_sending
        can_send = has_data and has_campaign and not_sending
        if self._current_campaign:
            status = self._current_campaign.get("status", "draft")
            if status == "completed":
                can_send = False

        self.start_btn.configure(state="normal" if can_send else "disabled")
        self.pause_btn.configure(state="normal" if self._is_sending else "disabled")
        self.cancel_btn.configure(state="normal" if self._is_sending else "disabled")

        has_failed = any(r.get("status") == "failed" for r in self._imported_data)
        self.retry_btn.configure(state="normal" if has_failed and not self._is_sending else "disabled")

        if can_send and not has_template:
            self.start_btn.configure(text=f"⚠ {tr('start_sending')}")
        else:
            self.start_btn.configure(text=f"▶ {tr('start_sending')}")

    def _populate_grid(self, data: Optional[List[Dict]] = None) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        records = data if data is not None else self._imported_data
        if not records:
            self.tree["columns"] = ["phone"]
            self.tree.heading("phone", text="Phone")
            self.tree.column("phone", width=200)
            self.records_count.configure(text=f"0 {tr('records')}")
            return

        all_keys = list(set(k for row in records for k in row.keys()))
        display_keys = [k for k in all_keys if k not in ("id",)]
        if "phone" in display_keys:
            display_keys.remove("phone")
            display_keys.insert(0, "phone")
        if "status" in display_keys:
            display_keys.remove("status")
            display_keys.append("status")
        if "id" in display_keys:
            display_keys.remove("id")

        self.tree["columns"] = display_keys
        for col in display_keys:
            self.tree.heading(col, text=col.capitalize())
            width = ThemeColors.GRID_COLUMN_WIDTHS.get(col, ThemeColors.GRID_COLUMN_WIDTHS["default"])
            self.tree.column(col, width=width, minwidth=80)

        seen_status = set()
        for row in records:
            values = [str(row.get(col, "")) for col in display_keys]
            item = self.tree.insert("", "end", values=values)
            status = row.get("status", "")
            if status == "failed":
                self.tree.tag_configure("failed", background=ThemeColors.ERROR_BG)
                self.tree.item(item, tags=("failed",))

        self.records_count.configure(text=f"{len(records)} {tr('records')}")

    def _import_file(self) -> None:
        filepath = filedialog.askopenfilename(
            title=tr("import_title"),
            filetypes=[("Supported files", "*.csv *.xlsx *.xls *.json"), ("CSV", "*.csv"),
                       ("Excel", "*.xlsx *.xls"), ("JSON", "*.json")],
        )
        if not filepath:
            return

        try:
            self._imported_data, self._imported_columns, fmt = self.import_service.import_from_file(filepath)
            self._populate_grid()
            self._auto_map_columns()
            self._auto_save_recipients()
            self._update_preview()
            self._update_send_button_state()
            self.logger.info(f"Imported {len(self._imported_data)} recipients from {filepath}")
        except Exception as e:
            messagebox.showerror(tr("import_error"), str(e))

    def _import_paste(self) -> None:
        dialog = ImportDialog(self.master.master if hasattr(self.master, "master") else self)
        self.wait_window(dialog)

        if dialog.result:
            self._imported_data = dialog.result["data"]
            self._imported_columns = dialog.result["columns"]
            self._populate_grid()
            self._auto_map_columns()
            self._auto_save_recipients()
            self._update_preview()
            self._update_send_button_state()

    def _auto_map_columns(self) -> None:
        if not self._imported_columns:
            return

        phone_col = Validators.detect_phone_column(self._imported_columns)
        self._column_mapping = {}
        if phone_col:
            self._column_mapping["phone"] = phone_col

        var_idx = 1
        for col in self._imported_columns:
            if col == phone_col:
                continue
            self._column_mapping[str(var_idx)] = col
            var_idx += 1

    def _map_columns(self) -> None:
        if not self._current_campaign:
            messagebox.showinfo(tr("info"), tr("create_campaign_first"))
            return

        template_id = self._current_campaign.get("template_id", 0)
        if template_id:
            template = self.template_service.get_template(template_id)
            template_vars = template.variables if template else []
        else:
            template_vars = [str(i) for i in range(1, len(self._imported_columns))]

        if not self._imported_columns:
            messagebox.showinfo(tr("info"), tr("import_recipients_first"))
            return

        dialog = SelectColumnsDialog(
            self.master.master if hasattr(self.master, "master") else self,
            self._imported_columns, template_vars,
        )
        self.wait_window(dialog)

        if dialog.result:
            self._column_mapping = dialog.result
            self._update_preview()

    def _search_grid(self) -> None:
        search_win = ctk.CTkToplevel(self)
        search_win.title(tr("search"))
        search_win.geometry("300x120")
        search_win.transient(self)
        search_win.grab_set()
        search_win.configure(fg_color=ThemeColors.BG_PRIMARY)

        ctk.CTkLabel(search_win, text=tr("search_phone"),
                      font=ctk.CTkFont(size=12)).pack(padx=20, pady=(15, 5), anchor="w")
        entry = ctk.CTkEntry(search_win, placeholder_text=tr("search_phone"),
                              fg_color=ThemeColors.BG_SECONDARY, border_width=1, border_color=ThemeColors.BORDER)
        entry.pack(padx=20, fill="x")

        def do_search():
            query = entry.get().strip().lower()
            if not query:
                self._populate_grid()
            else:
                filtered = [r for r in self._imported_data if query in str(r.get("phone", "")).lower()]
                self._populate_grid(filtered)
            search_win.destroy()

        ctk.CTkButton(search_win, text=tr("search"), command=do_search,
                       fg_color=ThemeColors.ACCENT, text_color="#ffffff",
                       corner_radius=6).pack(pady=8)

    def _delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        if not messagebox.askyesno(tr("confirm"), tr("delete_rows")):
            return

        indices = [self.tree.index(item) for item in selected]
        for idx in sorted(indices, reverse=True):
            if idx < len(self._imported_data):
                del self._imported_data[idx]

        self._populate_grid()
        self._update_send_button_state()

    def _preview_data(self) -> None:
        if not self._imported_data:
            messagebox.showinfo(tr("no_data"), tr("import_recipients_first"))
            return
        dialog = DataPreviewDialog(
            self.master.master if hasattr(self.master, "master") else self,
            self._imported_data, self._imported_columns or list(self._imported_data[0].keys()),
        )

    def _auto_save_recipients(self) -> None:
        if not self._current_campaign or not self._current_campaign.get("id"):
            return
        campaign_id = self._current_campaign["id"]
        self.campaign_service.import_recipients(campaign_id, self._imported_data,
                                                 phone_column=self._column_mapping.get("phone", "phone"),
                                                 variable_mapping=self._column_mapping)
        self._update_info_bar()

    def _update_preview(self) -> None:
        if not self._current_campaign:
            self._set_preview_text(tr("select_campaign_preview"))
            return

        template_id = self._current_campaign.get("template_id", 0)
        if not template_id:
            self._set_preview_text(tr("select_template_preview"))
            return

        template = self.template_service.get_template(template_id)
        if not template:
            self._set_preview_text(tr("template_not_found"))
            return

        sample_row = self._imported_data[0] if self._imported_data else {}
        preview = self.template_service.build_preview_from_row(template, sample_row, self._column_mapping)
        self._set_preview_text(preview)

    def _clear_all_campaigns(self) -> None:
        if not messagebox.askyesno(tr("clear_all"), "¿Eliminar TODAS las campañas y sus datos?\nEsto no se puede deshacer."):
            return
        self.db.delete_all_campaigns()
        self._current_campaign = None
        self._imported_data = []
        self._imported_columns = []
        self._column_mapping = {}
        self._edit_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0 / 0")
        self.stats_label.configure(text="")
        self._refresh_campaign_list()
        self._update_info_bar()
        self._update_send_button_state()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.records_count.configure(text=f"0 {tr('records')}")
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.results_count.configure(text=f"0 {tr('records')}")
        self._set_preview_text(tr("select_campaign_preview"))
        self.logger.info("All campaigns cleared")

    def _set_preview_text(self, text: str) -> None:
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)
        self.preview_text.configure(state="disabled")

    def _start_sending(self) -> None:
        if self._is_sending:
            return
        if not self._current_campaign:
            return

        campaign_id = self._current_campaign["id"]
        template_id = self._current_campaign.get("template_id", 0)
        if not template_id:
            messagebox.showwarning(tr("no_template"), tr("select_template_for_campaign"))
            return

        template = self.template_service.get_template(template_id)
        if not template:
            messagebox.showerror(tr("error"), tr("template_not_found"))
            return

        results = self.campaign_service.get_campaign_results(campaign_id)
        if not results:
            messagebox.showinfo(tr("no_recipients"), tr("import_before_sending"))
            return

        self._is_sending = True
        self._update_send_button_state()
        self.start_btn.configure(state="disabled", text=tr("sending"))

        results_data = [
            {"id": r.id, "phone": r.phone, "variables_used": r.variables_used}
            for r in results if r.status == "queued"
        ]

        self.sender_worker.start_sending(
            campaign_id=campaign_id,
            results=results_data,
            content_sid=template.content_sid,
            variable_order=template.variables,
            column_mapping=self._column_mapping,
        )

    def _toggle_pause(self) -> None:
        if self.sender_worker.is_paused:
            self.sender_worker.pause()
            self.pause_btn.configure(text=tr("paused"))
        else:
            self.sender_worker.resume()
            self.pause_btn.configure(text=tr("pause"))

    def _cancel_sending(self) -> None:
        if messagebox.askyesno(tr("confirm"), tr("cancel_sending")):
            self.sender_worker.cancel()
            self._is_sending = False
            self._update_send_button_state()
            self.start_btn.configure(text=f"▶ {tr('start_sending')}")

    def _retry_failed(self) -> None:
        if not self._current_campaign:
            return
        campaign_id = self._current_campaign["id"]
        self.sender_worker.retry_failed(campaign_id)

    def _on_progress_update(self, stats: Dict[str, Any]) -> None:
        total = stats.get("total", 0)
        sent = stats.get("sent", 0)
        failed = stats.get("failed", 0)
        processed = sent + failed

        if total > 0:
            self.progress_bar.set(processed / total)
        self.progress_label.configure(text=f"{processed} / {total}")
        self.stats_label.configure(text=f"✅ {sent}  ❌ {failed}  ⏳ {stats.get('queued', 0)}")

        elapsed = stats.get("elapsed", 0)
        if processed > 0 and elapsed > 0:
            rate = processed / elapsed
            remaining = (total - processed) / rate if rate > 0 else 0
            self.stats_label.configure(
                text=f"✅ {sent}  ❌ {failed}  ⏳ {stats.get('queued', 0)}  ⏱ {remaining:.0f}s"
            )

        self._update_info_bar()

    def _on_worker_log(self, level: str, message: str, **kwargs) -> None:
        pass

    def _on_send_complete(self, stats: Dict[str, Any]) -> None:
        self._is_sending = False
        self._update_send_button_state()
        self.start_btn.configure(text=f"▶ {tr('start_sending')}")
        self._update_info_bar()
        self._refresh_results()
        messagebox.showinfo(tr("complete"),
                             tr("sending_complete").format(sent=stats.get('sent', 0), failed=stats.get('failed', 0)))

    def _refresh_results(self) -> None:
        if not self._current_campaign:
            return

        campaign_id = self._current_campaign["id"]
        results = self.campaign_service.get_campaign_results(campaign_id)

        if not results:
            return

        columns = ["phone", "status", "twilio_sid", "error_message", "attempt_count"]
        self.results_tree["columns"] = columns
        for col in columns:
            self.results_tree.heading(col, text=col.replace("_", " ").title())
            self.results_tree.column(col, width=130, minwidth=80)

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for r in results:
            values = [r.phone, r.status, r.twilio_sid, r.error_message, str(r.attempt_count)]
            item = self.results_tree.insert("", "end", values=values)
            if r.status == "failed":
                self.results_tree.tag_configure("failed", background=ThemeColors.ERROR_BG)
                self.results_tree.item(item, tags=("failed",))

        self.results_count.configure(text=f"{len(results)} {tr('records')}")

    def _check_delivery_status(self) -> None:
        if not self._current_campaign:
            return
        campaign_id = self._current_campaign["id"]
        changes = self.campaign_service.check_and_update_delivery_status(campaign_id)
        self._refresh_results()
        self._update_info_bar()
        if changes:
            self.logger.info(f"Updated {changes} delivery status(es) from Twilio")

    def _export_results(self) -> None:
        if not self._current_campaign:
            return
        campaign_id = self._current_campaign["id"]
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")],
        )
        if filepath:
            try:
                results = self.campaign_service.get_campaign_results(campaign_id)
                data = [{"phone": r.phone, "status": r.status, "twilio_sid": r.twilio_sid,
                         "error": r.error_message} for r in results]
                if filepath.endswith(".csv"):
                    import csv
                    with open(filepath, "w", newline="", encoding="utf-8") as f:
                        w = csv.DictWriter(f, fieldnames=["phone", "status", "twilio_sid", "error"])
                        w.writeheader()
                        w.writerows(data)
                else:
                    import pandas as pd
                    pd.DataFrame(data).to_excel(filepath, index=False)
                self.logger.info(f"Results exported to {filepath}")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror(tr("error"), str(e))

    def refresh(self) -> None:
        self._refresh_campaign_list()
        self._update_info_bar()
        self._update_send_button_state()

    @staticmethod
    def _build_history_view(page, parent_frame) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=tr("campaign_history"),
                      font=ctk.CTkFont(size=22, weight="bold"),
                      text_color=ThemeColors.FG_PRIMARY).grid(row=0, column=0, sticky="w", padx=4, pady=(4, 12))

        search_frame = ctk.CTkFrame(frame, fg_color="transparent")
        search_frame.grid(row=0, column=1, sticky="e", padx=4, pady=(4, 12))
        search_entry = ctk.CTkEntry(search_frame, placeholder_text=tr("search_campaigns"), width=200,
                                     fg_color=ThemeColors.BG_SECONDARY, border_width=1, border_color=ThemeColors.BORDER)
        search_entry.grid(row=0, column=0, padx=4)

        tree_frame = ctk.CTkFrame(frame, fg_color=ThemeColors.BG_SECONDARY,
                                   corner_radius=8, border_width=1, border_color=ThemeColors.BORDER)
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=4)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        columns = ["id", "name", "template", "status", "total", "sent", "failed", "duration", "date"]
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        col_widths = {"id": 40, "name": 200, "template": 150, "status": 80,
                       "total": 60, "sent": 60, "failed": 60, "duration": 80, "date": 150}
        for col in columns:
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=col_widths.get(col, 100))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        def load_history():
            from services.campaign_service import CampaignService
            svc = CampaignService()
            campaigns = svc.get_all_campaigns(limit=500)
            for item in tree.get_children():
                tree.delete(item)
            for c in campaigns:
                values = [c.id, c.name, c.template_name, c.status, c.total,
                          c.sent + c.delivered, c.failed, f"{c.duration_secs:.1f}s", c.created_at[:10]]
                tree.insert("", "end", values=values)

        def on_search():
            query = search_entry.get().strip()
            for item in tree.get_children():
                tree.delete(item)
            if not query:
                load_history()
            else:
                from services.campaign_service import CampaignService
                svc = CampaignService()
                campaigns = svc.search_campaigns(query)
                for c in campaigns:
                    values = [c.id, c.name, c.template_name, c.status, c.total,
                              c.sent + c.delivered, c.failed, f"{c.duration_secs:.1f}s", c.created_at[:10]]
                    tree.insert("", "end", values=values)

        search_entry.bind("<Return>", lambda e: on_search())
        ctk.CTkButton(search_frame, text=tr("search"), command=on_search,
                       fg_color=ThemeColors.ACCENT, text_color="#ffffff", corner_radius=6, height=30, width=70).grid(row=0, column=1, padx=4)
        ctk.CTkButton(search_frame, text=tr("refresh"), command=load_history,
                       fg_color=ThemeColors.FG_SECONDARY, text_color="#ffffff", corner_radius=6, height=30, width=70).grid(row=0, column=2, padx=4)

        load_history()
        return frame
