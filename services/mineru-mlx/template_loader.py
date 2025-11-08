"""
Template loader for configurable document extraction.
Loads JSON templates for different document types (medical, legal, technical, general).
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel


class TemplateVariable(BaseModel):
    """Variable definition in a template (supports nested properties for hierarchical schemas)"""
    name: str
    description: str
    type: str
    required: bool = False
    properties: Optional[List['TemplateVariable']] = None  # For nested objects (Pydantic pattern)


class TemplateParameters(BaseModel):
    """LLM and processing parameters"""
    max_text_length: int = 20000
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: int = 120


class OutputFormat(BaseModel):
    """Output format configuration"""
    null_handling: str = "Use null for missing data (not 'N/A' or empty string)"
    strict_schema: bool = True
    include_confidence: bool = False


class ExtractionTemplate(BaseModel):
    """Complete extraction template"""
    id: str
    name: str
    description: str
    category: str
    system_prompt: str
    user_prompt_template: str
    variables: List[TemplateVariable]
    parameters: TemplateParameters
    output_format: OutputFormat


class TemplateLoader:
    """Loads and manages extraction templates"""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            # Default to config/templates/ directory
            templates_dir = os.path.join(
                os.path.dirname(__file__),
                "config",
                "templates"
            )

        self.templates_dir = Path(templates_dir)
        self._templates: Dict[str, ExtractionTemplate] = {}
        self._load_all_templates()

    def _load_all_templates(self):
        """Load all JSON templates from the templates directory"""
        if not self.templates_dir.exists():
            print(f"Warning: Templates directory not found: {self.templates_dir}")
            return

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    template = ExtractionTemplate(**template_data)
                    self._templates[template.id] = template
                    print(f"Loaded template: {template.id} - {template.name}")
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")

    def get_template(self, template_id: str) -> Optional[ExtractionTemplate]:
        """Get a specific template by ID"""
        return self._templates.get(template_id)

    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates"""
        return [
            {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category
            }
            for template in self._templates.values()
        ]

    def build_prompt(
        self,
        template: ExtractionTemplate,
        text: str,
        max_text_length: Optional[int] = None
    ) -> tuple[str, str]:
        """
        Build system and user prompts from template.

        Returns:
            tuple: (system_prompt, user_prompt)
        """
        # Use template's max_text_length unless overridden
        text_limit = max_text_length or template.parameters.max_text_length
        truncated_text = text[:text_limit]

        # Build variables list (supports hierarchical grouping)
        variables_list = self._build_variables_list(template.variables)

        # Build JSON schema for output
        json_schema = self._build_json_schema(template)

        # Replace placeholders in user prompt template
        user_prompt = template.user_prompt_template.format(
            variables_list=variables_list,
            text=truncated_text,
            json_schema=json_schema
        )

        return template.system_prompt, user_prompt

    def _build_json_schema(self, template: ExtractionTemplate) -> str:
        """Build a JSON schema description from template variables (supports nested hierarchies)"""
        schema_fields = []
        for var in template.variables:
            schema_fields.append(self._build_field_schema(var, indent=1))

        schema = "{\n" + ",\n".join(schema_fields) + "\n}"

        # Add null handling instruction
        if template.output_format.null_handling:
            schema += f"\n\n{template.output_format.null_handling}"

        return schema

    def _build_variables_list(self, variables: List[TemplateVariable], indent: int = 0) -> str:
        """Build human-readable variables list (supports nested hierarchies)"""
        lines = []
        for var in variables:
            indent_str = "  " * indent
            if var.properties:
                # Nested group
                lines.append(f"{indent_str}- {var.name}: {var.description}")
                lines.append(self._build_variables_list(var.properties, indent + 1))
            else:
                # Simple field
                lines.append(f"{indent_str}- {var.name}: {var.description}")
        return "\n".join(lines)

    def _build_field_schema(self, var: TemplateVariable, indent: int = 1) -> str:
        """Build schema for a single field (recursive for nested objects)"""
        indent_str = "  " * indent
        required_marker = " (required)" if var.required else " (optional)"

        # Handle nested objects (hierarchical pattern from Pydantic/Docugami)
        if var.properties:
            nested_fields = []
            for prop in var.properties:
                nested_fields.append(self._build_field_schema(prop, indent + 1))
            nested_schema = "{\n" + ",\n".join(nested_fields) + f"\n{indent_str}  }}"
            return f'{indent_str}"{var.name}": {nested_schema}{required_marker}'
        else:
            return f'{indent_str}"{var.name}": <{var.type}{required_marker}>'

    def get_default_template(self) -> ExtractionTemplate:
        """Get default template (general_document)"""
        default = self.get_template("general_document")
        if not default:
            # Fallback to any available template
            if self._templates:
                return list(self._templates.values())[0]
            raise ValueError("No templates available!")
        return default


# Global template loader instance
template_loader = TemplateLoader()
