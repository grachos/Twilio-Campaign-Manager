import json
import csv
import io
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

from utils.validators import Validators
from utils.logger import AppLogger


class ImportService:
    """Handles importing recipient data from various file formats.

    Supports CSV, Excel, JSON, and manual paste input. Auto-detects
    column types and phone columns.
    """

    def __init__(self) -> None:
        self.logger = AppLogger()

    def import_from_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """Import data from a file.

        Returns (data, columns, format_name).
        """
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            return self.import_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            return self.import_excel(file_path)
        elif ext == ".json":
            return self.import_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def import_csv(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
        try:
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
            df = df.fillna("")
            df.columns = df.columns.str.strip()
            data = df.to_dict(orient="records")
            columns = list(df.columns)
            self.logger.info(f"Imported {len(data)} rows from CSV: {os.path.basename(file_path)}")
            return data, columns, "csv"
        except Exception as e:
            self.logger.error(f"CSV import error: {e}")
            raise

    def import_excel(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
        try:
            df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
            df = df.fillna("")
            df.columns = df.columns.str.strip()
            data = df.to_dict(orient="records")
            columns = list(df.columns)
            self.logger.info(f"Imported {len(data)} rows from Excel: {os.path.basename(file_path)}")
            return data, columns, "excel"
        except Exception as e:
            self.logger.error(f"Excel import error: {e}")
            raise

    def import_json(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                raw = [raw]
            data = []
            for item in raw:
                row = {str(k).strip(): str(v) if v is not None else "" for k, v in item.items()}
                data.append(row)
            columns = list(set(k for row in data for k in row.keys()))
            self.logger.info(f"Imported {len(data)} rows from JSON: {os.path.basename(file_path)}")
            return data, columns, "json"
        except Exception as e:
            self.logger.error(f"JSON import error: {e}")
            raise

    def import_from_text(self, text: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """Import from pasted text (tab/comma separated)."""
        try:
            reader = csv.DictReader(io.StringIO(text))
            data = []
            for row in reader:
                clean = {k.strip(): v.strip() for k, v in row.items()}
                data.append(clean)
            columns = list(data[0].keys()) if data else []
            self.logger.info(f"Imported {len(data)} rows from pasted text")
            return data, columns, "paste"
        except Exception as e:
            self.logger.error(f"Text import error: {e}")
            raise

    def detect_columns(self, columns: List[str]) -> Dict[str, Optional[str]]:
        """Auto-detect phone and variable columns.

        Returns mapping like {"phone": "Phone", "var1": "Customer", ...}
        """
        mapping = {}
        phone_col = Validators.detect_phone_column(columns)
        if phone_col:
            mapping["phone"] = phone_col

        var_idx = 1
        for col in columns:
            if col == phone_col:
                continue
            mapping[str(var_idx)] = col
            var_idx += 1

        return mapping

    def get_preview_data(
        self, data: List[Dict[str, Any]], limit: int = 10
    ) -> List[Dict[str, Any]]:
        return data[:limit]

    def validate_imported_data(
        self, data: List[Dict[str, Any]],
        phone_column: str = "phone",
        variables: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        return Validators.validate_import_data(data, phone_column, variables)

    def count_rows(self, file_path: str) -> int:
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(file_path, nrows=1)
            return len(pd.read_csv(file_path, usecols=[0]))
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
            return len(df)
        elif ext == ".json":
            with open(file_path, "r") as f:
                data = json.load(f)
            return len(data) if isinstance(data, list) else 1
        return 0

    def read_file_head(self, file_path: str, n: int = 5) -> Tuple[List[Dict[str, Any]], List[str]]:
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False, nrows=n)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, dtype=str, keep_default_na=False, nrows=n)
        elif ext == ".json":
            with open(file_path, "r") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                raw = raw[:n]
            else:
                raw = [raw]
            return raw, list(raw[0].keys()) if raw else []
        else:
            raise ValueError(f"Unsupported format: {ext}")

        df = df.fillna("")
        df.columns = df.columns.str.strip()
        return df.to_dict(orient="records"), list(df.columns)
