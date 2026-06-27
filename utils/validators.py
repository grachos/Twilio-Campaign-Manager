import re
from typing import List, Dict, Tuple, Any, Optional


class Validators:
    """Collection of validation methods for phone numbers, templates, and rows."""

    PHONE_REGEX = re.compile(r"^\+?1?\d{10,15}$")
    WHATSAPP_PREFIX = "whatsapp:"
    SMS_PREFIX = "sms:"

    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Validate and normalize a phone number.

        Returns (is_valid, normalized_phone).
        """
        if not phone or not isinstance(phone, str):
            return False, ""

        phone = phone.strip()
        prefix = ""

        if phone.lower().startswith(Validators.WHATSAPP_PREFIX):
            prefix = Validators.WHATSAPP_PREFIX
            phone = phone[len(Validators.WHATSAPP_PREFIX):]
        elif phone.lower().startswith(Validators.SMS_PREFIX):
            prefix = Validators.SMS_PREFIX
            phone = phone[len(Validators.SMS_PREFIX):]

        phone = re.sub(r"[\s\-\(\)\.]", "", phone)

        if not Validators.PHONE_REGEX.match(phone):
            return False, ""

        return True, f"{prefix}{phone}"

    @staticmethod
    def validate_phones_bulk(phones: List[str]) -> List[Tuple[str, str, bool]]:
        """Validate multiple phones.

        Returns list of (original, normalized, is_valid).
        """
        results = []
        for p in phones:
            valid, normalized = Validators.validate_phone(p)
            results.append((p, normalized, valid))
        return results

    @staticmethod
    def validate_content_variables(
        variables: List[str], data: dict
    ) -> Tuple[bool, List[str]]:
        """Check that all required template variables have values in data.

        Returns (is_valid, list_of_missing_variables).
        """
        missing = []
        for var in variables:
            key = var.strip("{}").strip()
            value = data.get(key, "")
            if not value or value in ("nan", "None", ""):
                missing.append(var)
        return len(missing) == 0, missing

    @staticmethod
    def validate_row(
        row: dict,
        required_columns: List[str],
        phone_column: str = "phone",
        variables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate a single data row.

        Returns dict with keys: valid, phone_valid, missing_vars, errors.
        """
        errors = []
        phone_raw = str(row.get(phone_column, "")).strip()
        phone_valid, normalized = Validators.validate_phone(phone_raw)

        if not phone_raw:
            errors.append("Empty phone")
        elif not phone_valid:
            errors.append("Invalid phone format")

        missing_vars = []
        if variables:
            for var in variables:
                key = var.strip("{}").strip()
                value = str(row.get(key, "")).strip()
                if not value or value in ("nan", "None", "nan"):
                    missing_vars.append(var)

        is_valid = phone_valid and len(missing_vars) == 0
        return {
            "valid": is_valid,
            "phone_valid": phone_valid,
            "normalized_phone": normalized if phone_valid else phone_raw,
            "missing_vars": missing_vars,
            "errors": errors,
        }

    @staticmethod
    def detect_phone_column(columns: List[str]) -> Optional[str]:
        """Auto-detect the phone column from a list of column names."""
        phone_aliases = {
            "phone", "phones", "telephone", "tel", "mobile", "cell",
            "phone number", "phonenumber", "phone_number", "contact",
            "número", "telefono", "teléfono", "whatsapp", "celular",
        }
        col_lower = {c: c.lower().strip() for c in columns}
        for col, low in col_lower.items():
            if low in phone_aliases:
                return col
        for col, low in col_lower.items():
            if any(alias in low for alias in phone_aliases):
                return col
        return None

    @staticmethod
    def format_phone_display(phone: str) -> str:
        """Format a phone for display purposes."""
        cleaned = phone.replace(Validators.WHATSAPP_PREFIX, "").replace(Validators.SMS_PREFIX, "")
        if len(cleaned) >= 10:
            return f"{cleaned[:2]} {cleaned[2:6]} {cleaned[6:]}"
        return cleaned

    @staticmethod
    def validate_import_data(
        data: List[Dict[str, Any]],
        phone_column: str = "phone",
        variables: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Validate all rows in imported data.

        Returns list of validation result dicts.
        """
        results = []
        seen_phones: set = set()
        for idx, row in enumerate(data):
            validation = Validators.validate_row(row, [phone_column], phone_column, variables)

            phone_raw = str(row.get(phone_column, "")).strip()
            if phone_raw in seen_phones:
                validation["valid"] = False
                validation["errors"].append("Duplicate phone")
            seen_phones.add(phone_raw)

            all_empty = all(
                not str(v).strip() or str(v).strip() in ("nan", "None")
                for v in row.values()
            )
            if all_empty:
                validation["valid"] = False
                validation["errors"].append("Empty row")

            validation["row_index"] = idx
            results.append(validation)

        return results

    @staticmethod
    def detect_duplicates(data: List[Dict], phone_column: str = "phone") -> List[int]:
        """Return indices of duplicate phone rows."""
        seen: set = set()
        duplicates: List[int] = []
        for idx, row in enumerate(data):
            phone = str(row.get(phone_column, "")).strip().lower()
            if phone in seen:
                duplicates.append(idx)
            seen.add(phone)
        return duplicates
