from typing import Optional, Dict, Any, List
from tkinter import messagebox, ttk
import customtkinter as ctk

from config.settings import ThemeColors
from services.template_service import TemplateService
from services.export_service import ExportService
from utils.logger import AppLogger
from utils.i18n import tr
from database.models import Template
from ui.dialogs import TemplateDialog


class TemplatesPage(ctk.CTkFrame):
    """Template management page.

    Allows users to create, edit, delete, duplicate, and preview
    Twilio Content Templates. Each template defines the content_sid,
    variable placeholders, and example values.
    """

    def __init__(self, parent, toolbar, **kwargs):
        super().__init__(parent, fg_color=ThemeColors.BG_PRIMARY, **kwargs)
        self.toolbar = toolbar
        self.template_service = TemplateService()
        self.export_service = ExportService()
        self.logger = AppLogger()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text=tr('content_templates'),
                      font=ctk.CTkFont(size=20, weight="bold"),
                      text_color=ThemeColors.FG_PRIMARY).grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(btn_frame, text=f"➕ {tr('new_template')}",
                       fg_color=ThemeColors.ACCENT, hover_color=ThemeColors.ACCENT_HOVER,
                       command=self._new_template).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text=f"🔄 {tr('refresh')}",
                       fg_color=ThemeColors.BG_TERTIARY,
                       command=self._refresh_list).grid(row=0, column=1, padx=5)

        # Main content
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=2)
        content_frame.grid_rowconfigure(0, weight=1)

        # Left panel - template list
        list_frame = ctk.CTkFrame(content_frame, fg_color=ThemeColors.BG_SECONDARY, corner_radius=8)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(list_frame, text=tr('templates'),
                      font=ctk.CTkFont(size=14, weight="bold"),
                      text_color=ThemeColors.FG_PRIMARY).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        tree_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, columns=("name", "variables"), show="headings", height=15)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.heading("name", text="Name")
        self.tree.heading("variables", text="Variables")
        self.tree.column("name", width=180)
        self.tree.column("variables", width=100)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        # Right panel - detail view
        detail_frame = ctk.CTkFrame(content_frame, fg_color=ThemeColors.BG_SECONDARY, corner_radius=8)
        detail_frame.grid(row=0, column=1, sticky="nsew")
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(5, weight=1)

        self.detail_labels = {}
        row = 0
        for key, label in [
            ("name", tr('template_name')),
            ("description", tr('description')),
            ("content_sid", tr('content_sid')),
            ("variables", tr('variables')),
        ]:
            ctk.CTkLabel(detail_frame, text=label,
                          font=ctk.CTkFont(size=12, weight="bold"),
                          text_color=ThemeColors.FG_SECONDARY).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 2))
            row += 1
            lbl = ctk.CTkLabel(detail_frame, text="—",
                                font=ctk.CTkFont(size=13),
                                text_color=ThemeColors.FG_PRIMARY, anchor="w", justify="left")
            lbl.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 5))
            self.detail_labels[key] = lbl
            row += 1

        # Preview section
        ctk.CTkLabel(detail_frame, text=tr('preview'),
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color=ThemeColors.FG_SECONDARY).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 2))
        row += 1
        self.preview_box = ctk.CTkTextbox(detail_frame, height=100,
                                           fg_color=ThemeColors.INPUT_BG,
                                           text_color=ThemeColors.FG_PRIMARY)
        self.preview_box.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 15))
        self.preview_box.insert("1.0", tr('select_template_preview'))
        self.preview_box.configure(state="disabled")

        row += 1
        action_frame = ctk.CTkFrame(detail_frame, fg_color="transparent")
        action_frame.grid(row=row, column=0, pady=(0, 15))

        ctk.CTkButton(action_frame, text=f"✏ {tr('edit')}", fg_color=ThemeColors.INFO,
                       command=self._edit_template).grid(row=0, column=0, padx=5)
        ctk.CTkButton(action_frame, text=f"📋 {tr('duplicate')}", fg_color=ThemeColors.BG_TERTIARY,
                       command=self._duplicate_template).grid(row=0, column=1, padx=5)
        ctk.CTkButton(action_frame, text=f"🗑 {tr('delete')}", fg_color=ThemeColors.DANGER,
                       command=self._delete_template).grid(row=0, column=2, padx=5)
        ctk.CTkButton(action_frame, text=f"📤 {tr('export')}", fg_color=ThemeColors.BG_TERTIARY,
                       command=self._export_template).grid(row=0, column=3, padx=5)

        self._selected_template_id: Optional[int] = None

    def _refresh_list(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        templates = self.template_service.get_all_templates()
        for t in templates:
            self.tree.insert("", "end", iid=str(t.id), values=(t.name, str(t.variable_count)))

    def _on_select(self, event) -> None:
        selected = self.tree.selection()
        if not selected:
            return

        template_id = int(selected[0])
        self._selected_template_id = template_id
        template = self.template_service.get_template(template_id)
        if not template:
            return

        self.detail_labels["name"].configure(text=template.name)
        self.detail_labels["description"].configure(text=template.description or "—")
        self.detail_labels["content_sid"].configure(text=template.content_sid)
        vars_text = ", ".join(template.variables) if template.variables else tr('none')
        self.detail_labels["variables"].configure(text=vars_text)

        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        if template.examples:
            import json
            self.preview_box.insert("1.0", json.dumps(template.examples, indent=2))
        else:
            self.preview_box.insert("1.0", tr('no_example_values'))
        self.preview_box.configure(state="disabled")

    def _new_template(self) -> None:
        from ui.dialogs import TemplateDialog
        dialog = TemplateDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            try:
                self.template_service.create_template(
                    name=dialog.result["name"],
                    description=dialog.result.get("description", ""),
                    content_sid=dialog.result["content_sid"],
                    variables=dialog.result.get("variables", []),
                    examples=dialog.result.get("examples", {}),
                )
                self._refresh_list()
                self.logger.info(f"Template created: {dialog.result['name']}")
            except Exception as e:
                messagebox.showerror(tr('error'), str(e))

    def _edit_template(self) -> None:
        if not self._selected_template_id:
            messagebox.showinfo(tr('info'), tr('select_template_first'))
            return

        template = self.template_service.get_template(self._selected_template_id)
        if not template:
            return

        dialog = TemplateDialog(self, template.to_dict() if hasattr(template, 'to_dict') else {
            "name": template.name,
            "description": template.description,
            "content_sid": template.content_sid,
            "variables": template.variables,
            "examples": template.examples,
        })
        self.wait_window(dialog)

        if dialog.result:
            try:
                self.template_service.update_template(
                    template_id=self._selected_template_id,
                    name=dialog.result["name"],
                    description=dialog.result.get("description", ""),
                    content_sid=dialog.result["content_sid"],
                    variables=dialog.result.get("variables", []),
                    examples=dialog.result.get("examples", {}),
                )
                self._refresh_list()
                self.logger.info(f"Template updated: {dialog.result['name']}")
            except Exception as e:
                messagebox.showerror(tr('error'), str(e))

    def _duplicate_template(self) -> None:
        if not self._selected_template_id:
            return

        template = self.template_service.get_template(self._selected_template_id)
        if not template:
            return

        new_name = f"{template.name} ({tr('copy')})"
        try:
            self.template_service.duplicate_template(self._selected_template_id, new_name)
            self._refresh_list()
            self.logger.info(f"Template duplicated: {new_name}")
        except Exception as e:
            messagebox.showerror(tr('error'), str(e))

    def _delete_template(self) -> None:
        if not self._selected_template_id:
            return
        if not messagebox.askyesno(tr('confirm'), tr('delete_template_confirm')):
            return

        self.template_service.delete_template(self._selected_template_id)
        self._selected_template_id = None
        self._refresh_list()
        for lbl in self.detail_labels.values():
            lbl.configure(text="—")
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", tr('select_template_preview'))
        self.preview_box.configure(state="disabled")

    def _export_template(self) -> None:
        if not self._selected_template_id:
            return
        template = self.template_service.get_template(self._selected_template_id)
        if not template:
            return

        try:
            filepath = self.export_service.export_json([template.to_dict()])
            messagebox.showinfo(tr('exported'), f"{tr('template_exported_to')}\n{filepath}")
        except Exception as e:
            messagebox.showerror(tr('error'), str(e))
