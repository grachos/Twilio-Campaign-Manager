import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from typing import Optional, List, Dict, Any, Tuple
import customtkinter as ctk

from config.settings import ThemeColors
from utils.i18n import tr


class BaseDialog(ctk.CTkToplevel):
    """Base class for all modal dialogs with dark theme."""

    def __init__(self, parent, title: str, width: int = 500, height: int = 400):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.result = None

        self.configure(fg_color=ThemeColors.BG_PRIMARY)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.center_on_parent(parent, width, height)

    def center_on_parent(self, parent, width: int, height: int) -> None:
        self.update_idletasks()
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class CampaignDialog(BaseDialog):
    """Dialog for creating or editing a campaign."""

    def __init__(self, parent, templates: List[str],
                 campaign_data: Optional[Dict] = None):
        title = tr('edit_campaign') if campaign_data else tr('new_campaign')
        super().__init__(parent, title, width=550, height=400)
        self.templates = templates
        self.campaign_data = campaign_data
        self.result: Optional[Dict] = None
        self._build_ui()
        if campaign_data:
            self._populate(campaign_data)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=0)

        row = 0
        ctk.CTkLabel(self, text=tr('campaign_name'), anchor="w",
                      font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(20, 5))
        row += 1
        self.name_entry = ctk.CTkEntry(self, placeholder_text=tr('enter_campaign_name'))
        self.name_entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5)

        row += 1
        ctk.CTkLabel(self, text=tr('description'), anchor="w",
                      font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 5))
        row += 1
        self.desc_entry = ctk.CTkEntry(self, placeholder_text=tr('optional_description'))
        self.desc_entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5)

        row += 1
        ctk.CTkLabel(self, text=tr('select_template'), anchor="w",
                      font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 5))
        row += 1
        self.template_var = ctk.StringVar(value="")
        self.template_menu = ctk.CTkOptionMenu(
            self, variable=self.template_var,
            values=self.templates if self.templates else [tr('no_templates_available')],
            fg_color=ThemeColors.INPUT_BG, button_color=ThemeColors.ACCENT,
        )
        self.template_menu.grid(row=row, column=0, sticky="ew", padx=20, pady=5)

        row += 1
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, pady=25)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_frame, text=tr('cancel'), fg_color=ThemeColors.BG_TERTIARY,
                       hover_color="#1a1a4e", width=120, command=self._cancel).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text=tr('save'), fg_color=ThemeColors.ACCENT,
                       hover_color=ThemeColors.ACCENT_HOVER, width=120, command=self._save).grid(row=0, column=1, padx=10)

    def _populate(self, data: Dict) -> None:
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, data.get("name", ""))
        self.desc_entry.delete(0, "end")
        self.desc_entry.insert(0, data.get("description", ""))
        tmpl_name = data.get("template_name", "")
        if tmpl_name in self.templates:
            self.template_var.set(tmpl_name)

    def _save(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning(tr('validation'), tr('campaign_name_required'), parent=self)
            return
        self.result = {
            "name": name,
            "description": self.desc_entry.get().strip(),
            "template_name": self.template_var.get(),
        }
        self.destroy()


class TemplateDialog(BaseDialog):
    """Dialog for creating or editing a template."""

    def __init__(self, parent, template_data: Optional[Dict] = None):
        title = tr('edit_template') if template_data else tr('new_template')
        super().__init__(parent, title, width=600, height=550)
        self.template_data = template_data
        self.result: Optional[Dict] = None
        self._build_ui()
        if template_data:
            self._populate(template_data)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        row = 0
        ctk.CTkLabel(self, text=tr('template_name'), anchor="w",
                      font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(20, 5))
        row += 1
        self.name_entry = ctk.CTkEntry(self, placeholder_text=tr('eg_shipment_notification'))
        self.name_entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5)

        row += 1
        ctk.CTkLabel(self, text=tr('description'), anchor="w",
                      font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 5))
        row += 1
        self.desc_entry = ctk.CTkEntry(self, placeholder_text=tr('template_description'))
        self.desc_entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5)

        row += 1
        ctk.CTkLabel(self, text=tr('content_sid'), anchor="w",
                      font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 5))
        row += 1
        self.sid_entry = ctk.CTkEntry(self, placeholder_text=tr('eg_content_sid'))
        self.sid_entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5)

        row += 1
        ctk.CTkLabel(self, text=tr('variables_label'),
                      anchor="w", font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 5))
        row += 1
        self.vars_entry = ctk.CTkEntry(self, placeholder_text="{{1}}, {{2}}, {{3}}")
        self.vars_entry.grid(row=row, column=0, sticky="ew", padx=20, pady=5)

        row += 1
        ctk.CTkLabel(self, text=tr('example_values'),
                      anchor="w", font=ctk.CTkFont(size=13)).grid(row=row, column=0, sticky="w", padx=20, pady=(15, 5))
        row += 1
        self.examples_text = ctk.CTkTextbox(self, height=80)
        self.examples_text.grid(row=row, column=0, sticky="ew", padx=20, pady=5)
        self.examples_text.insert("1.0", '{"1": "John", "2": "Order 55", "3": "TRK-123"}')

        row += 1
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, pady=20)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_frame, text=tr('cancel'), fg_color=ThemeColors.BG_TERTIARY,
                       hover_color="#1a1a4e", width=120, command=self._cancel).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text=tr('save'), fg_color=ThemeColors.ACCENT,
                       hover_color=ThemeColors.ACCENT_HOVER, width=120, command=self._save).grid(row=0, column=1, padx=10)

    def _populate(self, data: Dict) -> None:
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, data.get("name", ""))
        self.desc_entry.delete(0, "end")
        self.desc_entry.insert(0, data.get("description", ""))
        self.sid_entry.delete(0, "end")
        self.sid_entry.insert(0, data.get("content_sid", ""))
        variables = data.get("variables", [])
        self.vars_entry.delete(0, "end")
        self.vars_entry.insert(0, ", ".join(variables))
        examples = data.get("examples", {})
        import json
        self.examples_text.delete("1.0", "end")
        self.examples_text.insert("1.0", json.dumps(examples, indent=2))

    def _save(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning(tr('validation'), tr('template_name_required'), parent=self)
            return
        sid = self.sid_entry.get().strip()
        if not sid:
            messagebox.showwarning(tr('validation'), tr('content_sid_required'), parent=self)
            return

        vars_text = self.vars_entry.get().strip()
        variables = [v.strip() for v in vars_text.split(",") if v.strip()] if vars_text else []

        examples = {}
        ex_text = self.examples_text.get("1.0", "end").strip()
        if ex_text:
            try:
                import json
                examples = json.loads(ex_text)
            except json.JSONDecodeError:
                messagebox.showwarning(tr('validation'), tr('invalid_json_examples'), parent=self)
                return

        self.result = {
            "name": name,
            "description": self.desc_entry.get().strip(),
            "content_sid": sid,
            "variables": variables,
            "examples": examples,
        }
        self.destroy()


class ImportDialog(BaseDialog):
    """Dialog for importing recipients with various options."""

    def __init__(self, parent):
        super().__init__(parent, tr('import_recipients'), width=700, height=500)
        self.result: Optional[Dict] = None
        self._data: List[Dict] = []
        self._columns: List[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        tab_view = ctk.CTkTabview(self, fg_color=ThemeColors.BG_SECONDARY)
        tab_view.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))

        csv_tab = tab_view.add("CSV")
        excel_tab = tab_view.add("Excel")
        json_tab = tab_view.add("JSON")

        for tab in (csv_tab, excel_tab, json_tab):
            tab.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(csv_tab, text=tr('browse_csv_file'),
                       command=lambda: self._browse_file("csv")).pack(pady=20)
        ctk.CTkButton(excel_tab, text=tr('browse_excel_file'),
                       command=lambda: self._browse_file("excel")).pack(pady=20)
        ctk.CTkButton(json_tab, text=tr('browse_json_file'),
                       command=lambda: self._browse_file("json")).pack(pady=20)

        ctk.CTkLabel(self, text=tr('paste_data_label'),
                      anchor="w", font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", padx=20, pady=(10, 5))

        self.paste_text = ctk.CTkTextbox(self, height=120)
        self.paste_text.grid(row=2, column=0, sticky="ew", padx=20, pady=5)

        self.preview_label = ctk.CTkLabel(self, text="", anchor="w",
                                           font=ctk.CTkFont(size=11))
        self.preview_label.grid(row=3, column=0, sticky="nw", padx=20, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=15)
        ctk.CTkButton(btn_frame, text=tr('cancel'), fg_color=ThemeColors.BG_TERTIARY,
                       width=120, command=self._cancel).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text=tr('import_data'), fg_color=ThemeColors.ACCENT,
                       width=120, command=self._import_data).grid(row=0, column=1, padx=10)

    def _browse_file(self, fmt: str) -> None:
        ext_map = {"csv": "*.csv", "excel": "*.xlsx *.xls", "json": "*.json"}
        ext = ext_map.get(fmt, "*.*")
        filepath = filedialog.askopenfilename(
            title=f"{tr('select')} {fmt.upper()} {tr('file')}",
            filetypes=[(f"{fmt.upper()} files", ext)],
        )
        if filepath:
            try:
                from services.import_service import ImportService
                svc = ImportService()
                self._data, self._columns, _ = svc.import_from_file(filepath)
                self._file_path = filepath
                self.preview_label.configure(
                    text=f"{tr('loaded')} {len(self._data)} {tr('rows')} | {tr('columns')}: {', '.join(self._columns[:10])}"
                )
            except Exception as e:
                messagebox.showerror(tr('import_error'), str(e), parent=self)

    def _import_data(self) -> None:
        paste = self.paste_text.get("1.0", "end").strip()
        if paste and not self._data:
            try:
                from services.import_service import ImportService
                svc = ImportService()
                self._data, self._columns, _ = svc.import_from_text(paste)
            except Exception as e:
                messagebox.showerror(tr('import_error'), str(e), parent=self)
                return

        if not self._data:
            messagebox.showwarning(tr('no_data'), tr('no_data_message'), parent=self)
            return

        self.result = {
            "data": self._data,
            "columns": self._columns,
        }
        self.destroy()


class SettingsDialog(BaseDialog):
    """Dialog for editing settings in a modal form."""

    def __init__(self, parent, settings: Dict[str, str]):
        super().__init__(parent, tr('edit_settings'), width=500, height=300)
        self.settings = settings
        self.result: Optional[Dict[str, str]] = None
        self._entries: Dict[str, ctk.CTkEntry] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        row = 0
        for key, value in self.settings.items():
            ctk.CTkLabel(self, text=key, anchor="w",
                          font=ctk.CTkFont(size=12)).grid(row=row, column=0, sticky="w", padx=(20, 5), pady=5)
            show = "*" if "TOKEN" in key.upper() or "AUTH" in key.upper() else ""
            entry = ctk.CTkEntry(self, show=show)
            entry.insert(0, value)
            entry.grid(row=row, column=1, sticky="ew", padx=(0, 20), pady=5)
            self._entries[key] = entry
            row += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ctk.CTkButton(btn_frame, text=tr('cancel'), fg_color=ThemeColors.BG_TERTIARY,
                       width=120, command=self._cancel).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text=tr('save'), fg_color=ThemeColors.ACCENT,
                       width=120, command=self._save).grid(row=0, column=1, padx=10)

    def _save(self) -> None:
        self.result = {key: entry.get() for key, entry in self._entries.items()}
        self.destroy()


class AboutDialog(BaseDialog):
    def __init__(self, parent):
        super().__init__(parent, tr('about_title'), width=400, height=300)
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(self, text=tr('app_name'),
                      font=ctk.CTkFont(size=20, weight="bold"),
                      text_color=ThemeColors.ACCENT).pack(pady=(40, 10))
        ctk.CTkLabel(self, text=f"{tr('version')} 1.0.0",
                      font=ctk.CTkFont(size=13)).pack(pady=5)
        ctk.CTkLabel(self, text=tr('about_description'),
                      font=ctk.CTkFont(size=12)).pack(pady=10)
        ctk.CTkLabel(self, text=tr('about_tech_stack'),
                      font=ctk.CTkFont(size=11),
                      text_color=ThemeColors.FG_SECONDARY).pack(pady=5)
        ctk.CTkButton(self, text=tr('close'), fg_color=ThemeColors.ACCENT,
                       command=self.destroy).pack(pady=30)


class SelectColumnsDialog(BaseDialog):
    """Dialog for mapping columns to template variables."""

    def __init__(self, parent, columns: List[str], template_vars: List[str]):
        super().__init__(parent, tr('map_columns'), width=500, height=400)
        self.columns = columns
        self.template_vars = template_vars
        self.result: Optional[Dict[str, str]] = None
        self._mappings: Dict[str, ctk.CTkOptionMenu] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=tr('phone_column'),
                      font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        self.phone_var = ctk.StringVar(value=self.columns[0] if self.columns else "")
        ctk.CTkOptionMenu(self, variable=self.phone_var, values=self.columns,
                           fg_color=ThemeColors.INPUT_BG, button_color=ThemeColors.ACCENT
                           ).grid(row=0, column=1, sticky="ew", padx=20, pady=(20, 5))

        row = 1
        for var in self.template_vars:
            ctk.CTkLabel(self, text=f"{var}",
                          font=ctk.CTkFont(size=12)).grid(row=row, column=0, sticky="w", padx=20, pady=5)
            var_menu = ctk.CTkOptionMenu(
                self,
                values=[tr('skip')] + self.columns,
                fg_color=ThemeColors.INPUT_BG, button_color=ThemeColors.ACCENT,
            )
            idx = row - 1
            if idx < len(self.columns):
                var_menu.set(self.columns[idx])
            var_menu.grid(row=row, column=1, sticky="ew", padx=20, pady=5)
            self._mappings[var] = var_menu
            row += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ctk.CTkButton(btn_frame, text=tr('cancel'), fg_color=ThemeColors.BG_TERTIARY,
                       width=120, command=self._cancel).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text=tr('confirm'), fg_color=ThemeColors.ACCENT,
                       width=120, command=self._confirm).grid(row=0, column=1, padx=10)

    def _confirm(self) -> None:
        mapping = {"phone": self.phone_var.get()}
        for var, menu in self._mappings.items():
            col = menu.get()
            if col != tr('skip'):
                key = var.strip("{}").strip()
                mapping[key] = col
        self.result = mapping
        self.destroy()


class DataPreviewDialog(BaseDialog):
    """Dialog showing a preview of imported data in a table."""

    def __init__(self, parent, data: List[Dict], columns: List[str],
                 title: str = tr('data_preview')):
        super().__init__(parent, title, width=800, height=500)
        self.data = data
        self.columns = columns
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        frame = ctk.CTkFrame(self, fg_color=ThemeColors.BG_SECONDARY)
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings", height=15)
        for col in self.columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, minwidth=80)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        for row in self.data[:100]:
            values = [str(row.get(c, "")) for c in self.columns]
            tree.insert("", "end", values=values)

        count_label = ctk.CTkLabel(
            frame, text=f"{tr('showing')} {min(len(self.data), 100)} {tr('of')} {len(self.data)} {tr('rows')}",
            font=ctk.CTkFont(size=11))
        count_label.grid(row=1, column=0, pady=5)

        ctk.CTkButton(self, text=tr('close'), fg_color=ThemeColors.ACCENT,
                       command=self.destroy).grid(row=1, column=0, pady=10)
