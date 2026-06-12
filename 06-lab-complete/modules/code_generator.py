"""
Code Generation Tool — Generates complete Python visualization scripts
from ChartConfig and DataSchema.
"""

from typing import Optional
from templates.chart_templates import CHART_TEMPLATES
import config


class PythonCodeGenerator:
    """Generates Python code for medical data visualization."""

    def generate(self, chart_config: dict, schema_columns: list, data_path: str = "DATA_FILE_PATH") -> str:
        """
        Generate a complete Python script for the given chart configuration.

        Args:
            chart_config: ChartConfig dict with chart_type, axes, palette, etc.
            schema_columns: List of column info dicts
            data_path: Path to the CSV data file

        Returns:
            Complete Python script string
        """
        chart_type = chart_config.get("chart_type", "eda_dashboard")
        template = CHART_TEMPLATES.get(chart_type)

        if template:
            return self._fill_template(template, chart_config, schema_columns, data_path)
        else:
            # Fallback: generate from scratch
            return self._generate_generic(chart_config, schema_columns, data_path)

    def patch_code(self, current_code: str, edit_instruction: str) -> str:
        """
        Apply a simple edit to existing code based on instruction.
        This is a basic version — the LLM orchestrator handles complex patches.
        """
        # Simple replacements for common edits
        edits = {
            "red": ("#FF5722", "#E74C3C", "red"),
            "blue": ("#2196F3", "#3498DB", "blue"),
            "green": ("#4CAF50", "#2ECC71", "green"),
            "xanh lá": ("#4CAF50", "#2ECC71", "green"),
            "xanh dương": ("#2196F3", "#3498DB", "blue"),
            "đỏ": ("#FF5722", "#E74C3C", "red"),
        }

        # This is a simplistic patcher — the real patching happens via LLM
        return current_code

    def _fill_template(self, template: str, chart_config: dict, schema_columns: list, data_path: str) -> str:
        """Fill a chart template with actual values."""
        # Get palette colors
        palette_name = chart_config.get("color_palette", "colorblind_safe")
        palette = config.MEDICAL_PALETTES.get(palette_name, config.MEDICAL_PALETTES["default"])
        if isinstance(palette, list):
            palette_str = str(palette)
        else:
            palette_str = f'"{palette}"'

        # Build replacements
        replacements = {
            "{{DATA_PATH}}": f'"{data_path}"' if not data_path.startswith('"') else data_path,
            "{{OUTPUT_PATH}}": '"OUTPUT_FILE_PATH"',
            "{{X_AXIS}}": chart_config.get("x_axis", ""),
            "{{Y_AXIS}}": chart_config.get("y_axis", ""),
            "{{HUE}}": chart_config.get("hue", ""),
            "{{TITLE}}": chart_config.get("title", "Medical Data Visualization"),
            "{{XLABEL}}": chart_config.get("xlabel", ""),
            "{{YLABEL}}": chart_config.get("ylabel", ""),
            "{{PALETTE}}": palette_str,
            "{{FIGSIZE_W}}": str(chart_config.get("figure_size", [12, 7])[0]),
            "{{FIGSIZE_H}}": str(chart_config.get("figure_size", [12, 7])[1]),
            "{{DPI}}": str(chart_config.get("dpi", 150)),
        }

        # Handle extra params
        extra = chart_config.get("extra_params", {})
        if "columns" in extra:
            replacements["{{COLUMNS}}"] = str(extra["columns"])
        if "method" in extra:
            replacements["{{METHOD}}"] = extra["method"]
        if "numeric_columns" in extra:
            replacements["{{NUMERIC_COLUMNS}}"] = str(extra["numeric_columns"])
        if "categorical_columns" in extra:
            replacements["{{CATEGORICAL_COLUMNS}}"] = str(extra["categorical_columns"])

        # Apply replacements
        code = template
        for key, val in replacements.items():
            code = code.replace(key, str(val))

        return code

    def _generate_generic(self, chart_config: dict, schema_columns: list, data_path: str) -> str:
        """Generate a generic visualization script when no template matches."""
        x_axis = chart_config.get("x_axis", "")
        y_axis = chart_config.get("y_axis", "")
        title = chart_config.get("title", "Data Visualization")

        code = f'''import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# ── Configuration ──────────────────────────────────────────────
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.size'] = 12
plt.rcParams['figure.facecolor'] = 'white'

# ── Data Loading ───────────────────────────────────────────────
df = pd.read_csv("{data_path}")
print(f"Loaded: {{df.shape[0]}} rows × {{df.shape[1]}} columns")
print(f"Columns: {{list(df.columns)}}")

# ── Visualization ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
'''
        if x_axis and y_axis:
            code += f'''
sns.scatterplot(data=df, x="{x_axis}", y="{y_axis}", ax=ax, alpha=0.7)
ax.set_title("{title}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{x_axis}", fontsize=13)
ax.set_ylabel("{y_axis}", fontsize=13)
'''
        else:
            code += f'''
# Auto-select first numeric columns for visualization
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
if len(numeric_cols) >= 2:
    sns.scatterplot(data=df, x=numeric_cols[0], y=numeric_cols[1], ax=ax, alpha=0.7)
    ax.set_title("{title}", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel(numeric_cols[0], fontsize=13)
    ax.set_ylabel(numeric_cols[1], fontsize=13)
elif len(numeric_cols) >= 1:
    sns.histplot(data=df, x=numeric_cols[0], kde=True, ax=ax, color="#0072B2")
    ax.set_title("{title}", fontsize=16, fontweight='bold', pad=20)
'''

        code += '''
# ── Export ─────────────────────────────────────────────────────
plt.tight_layout()
plt.savefig("OUTPUT_FILE_PATH", dpi=150, bbox_inches='tight', facecolor='white')
print("Chart saved successfully!")
'''
        return code
