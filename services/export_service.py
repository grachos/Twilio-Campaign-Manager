import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import pandas as pd

from config.config import ConfigManager
from utils.logger import AppLogger


class ExportService:
    """Handles exporting campaign data to various formats.

    Supports CSV, Excel, JSON, and PDF report generation with
    consistent formatting and styling.
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.logger = AppLogger()
        self._ensure_export_dir()

    def _ensure_export_dir(self) -> None:
        Path(self.config.exports_dir).mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, base_name: str, ext: str) -> str:
        timestamp = datetime.now().strftime(self.config.get("EXPORT_DATE_FORMAT", "%Y%m%d_%H%M%S"))
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in base_name)
        return os.path.join(self.config.exports_dir, f"{safe_name}_{timestamp}.{ext}")

    def export_csv(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        if not data:
            raise ValueError("No data to export")
        filepath = filename or self._generate_filename("export", "csv")
        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
                writer.writeheader()
                writer.writerows(data)
            self.logger.info(f"Exported {len(data)} rows to CSV: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"CSV export error: {e}")
            raise

    def export_excel(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        if not data:
            raise ValueError("No data to export")
        filepath = filename or self._generate_filename("export", "xlsx")
        try:
            df = pd.DataFrame(data)
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Campaign Results", index=False)
                worksheet = writer.sheets["Campaign Results"]
                for column in df:
                    col_idx = df.columns.get_loc(column) + 1
                    max_len = max(
                        df[column].astype(str).map(len).max() if len(df) > 0 else 0,
                        len(str(column)),
                    )
                    worksheet.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else "A"].width = min(max_len + 2, 50)
            self.logger.info(f"Exported {len(data)} rows to Excel: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Excel export error: {e}")
            raise

    def export_json(self, data: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
        if not data:
            raise ValueError("No data to export")
        filepath = filename or self._generate_filename("export", "json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Exported {len(data)} rows to JSON: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"JSON export error: {e}")
            raise

    def export_pdf_report(
        self,
        data: List[Dict[str, Any]],
        campaign_name: str,
        stats: Optional[Dict[str, int]] = None,
        filename: Optional[str] = None,
    ) -> str:
        if not data:
            raise ValueError("No data to export")
        filepath = filename or self._generate_filename("report", "pdf")
        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            title_style = ParagraphStyle(
                "CampaignTitle",
                parent=styles["Title"],
                fontSize=18,
                spaceAfter=20,
            )
            elements.append(Paragraph(f"Campaign Report: {campaign_name}", title_style))
            elements.append(Spacer(1, 12))

            if stats:
                stat_style = ParagraphStyle("Stats", parent=styles["Normal"], fontSize=11, spaceAfter=6)
                stats_text = (
                    f"Total: {stats.get('total', 0)} | "
                    f"Sent: {stats.get('sent', 0)} | "
                    f"Delivered: {stats.get('delivered', 0)} | "
                    f"Failed: {stats.get('failed', 0)}"
                )
                elements.append(Paragraph(stats_text, stat_style))
                elements.append(Spacer(1, 12))

            table_data = [list(data[0].keys())]
            for row in data:
                table_data.append([str(v) for v in row.values()])

            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#e8e8e8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2a2a4a")),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#1a1a2e"), colors.HexColor("#16213e")]),
            ]))
            elements.append(table)

            doc.build(elements)
            self.logger.info(f"PDF report generated: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"PDF export error: {e}")
            raise

    def export_configuration(self, config_data: Dict[str, Any]) -> str:
        filepath = self._generate_filename("config", "json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Configuration exported: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Config export error: {e}")
            raise

    def import_configuration(self, filepath: str) -> Dict[str, Any]:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.logger.info(f"Configuration imported: {filepath}")
        return data
