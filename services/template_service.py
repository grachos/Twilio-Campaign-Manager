from typing import List, Optional, Dict, Any
from database.database import DatabaseManager
from database.models import Template
from config.config import ConfigManager
from utils.logger import AppLogger


class TemplateService:
    """Manages Twilio Content Templates.

    Provides CRUD operations, preview generation, and variable
    management for message templates.
    """

    def __init__(self) -> None:
        self.db = DatabaseManager()
        self.config = ConfigManager()
        self.logger = AppLogger()

    def create_template(
        self,
        name: str,
        description: str,
        content_sid: str,
        variables: Optional[List[str]] = None,
        examples: Optional[Dict[str, str]] = None,
    ) -> int:
        if variables is None:
            variables = []
        if examples is None:
            examples = {}

        template_id = self.db.save_template(name, description, content_sid, variables, examples)
        self.logger.info(f"Template created: {name} (ID: {template_id})")
        return template_id

    def update_template(
        self,
        template_id: int,
        name: str,
        description: str,
        content_sid: str,
        variables: Optional[List[str]] = None,
        examples: Optional[Dict[str, str]] = None,
    ) -> None:
        if variables is None:
            variables = []
        if examples is None:
            examples = {}
        self.db.update_template(template_id, name, description, content_sid, variables, examples)
        self.logger.info(f"Template updated: {name} (ID: {template_id})")

    def delete_template(self, template_id: int) -> None:
        template = self.get_template(template_id)
        if template:
            self.db.delete_template(template_id)
            self.logger.info(f"Template deleted: {template.name} (ID: {template_id})")

    def get_template(self, template_id: int) -> Optional[Template]:
        data = self.db.get_template(template_id)
        return Template.from_dict(data) if data else None

    def get_all_templates(self) -> List[Template]:
        return [Template.from_dict(d) for d in self.db.get_all_templates()]

    def get_template_names(self) -> List[str]:
        return [t.name for t in self.get_all_templates()]

    def generate_preview(
        self,
        template: Template,
        variable_values: Dict[str, str],
        message_prefix: str = "",
    ) -> str:
        """Generate a preview of how the message will look.

        Uses example values where actual values are missing.
        """
        if not template.variables:
            return message_prefix + " (no variables)"

        preview = message_prefix
        placeholders = {}
        for var in template.variables:
            key = var.strip("{}").strip()
            value = variable_values.get(key, template.examples.get(key, f"{{{{{key}}}}}"))
            placeholders[f"{{{{{key}}}}}"] = value
            placeholders[var] = value

        if template.examples:
            preview = template.examples.get("body", "") or template.examples.get("preview", "")
            if not preview:
                parts = []
                for var in template.variables:
                    key = var.strip("{}").strip()
                    val = placeholders.get(f"{{{{{key}}}}}", f"[{key}]")
                    parts.append(f"{key}: {val}")
                preview = " | ".join(parts)

        for placeholder, value in placeholders.items():
            preview = preview.replace(placeholder, str(value))

        return preview

    def build_preview_from_row(
        self,
        template: Template,
        row: Dict[str, str],
        column_mapping: Dict[str, str],
    ) -> str:
        """Build preview from a data row using column mapping."""
        variable_values = {}
        for var in template.variables:
            key = var.strip("{}").strip()
            col_name = column_mapping.get(key, key)
            value = str(row.get(col_name, ""))
            if value.lower() in ("nan", "none", "null"):
                value = ""
            variable_values[key] = value or template.examples.get(key, f"[{key}]")
        return self.generate_preview(template, variable_values)

    def get_variables_from_template(self, template_id: int) -> List[str]:
        template = self.get_template(template_id)
        return template.variables if template else []

    def validate_template_name_unique(self, name: str, exclude_id: Optional[int] = None) -> bool:
        templates = self.get_all_templates()
        for t in templates:
            if t.name.lower() == name.lower() and t.id != exclude_id:
                return False
        return True

    def duplicate_template(self, template_id: int, new_name: str) -> int:
        original = self.get_template(template_id)
        if not original:
            raise ValueError(f"Template {template_id} not found")
        return self.create_template(
            name=new_name,
            description=original.description,
            content_sid=original.content_sid,
            variables=list(original.variables),
            examples=dict(original.examples),
        )
