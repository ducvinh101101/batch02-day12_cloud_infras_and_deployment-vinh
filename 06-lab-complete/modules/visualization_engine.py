"""
Visualization Decision Engine — decides the optimal chart type
based on data structure, user intent, and medical domain context.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import config


# ── Data Classes ────────────────────────────────────────────────────

@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    chart_type: str
    library: str  # matplotlib, seaborn, plotly
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    hue: Optional[str] = None  # grouping / color variable
    color_palette: str = "colorblind_safe"
    statistical_annotations: list = field(default_factory=list)
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    figure_size: list = field(default_factory=lambda: [12, 7])
    dpi: int = 150
    extra_params: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


# ── Intent Keywords ─────────────────────────────────────────────────

COMPARISON_KEYWORDS = [
    "so sánh", "so sanh", "khác nhau", "khac nhau", "nhóm", "nhom",
    "compare", "comparison", "difference", "between groups", "versus", "vs",
    "giữa", "giua", "hơn", "hon", "khác biệt", "khac biet",
]

TREND_KEYWORDS = [
    "xu hướng", "xu huong", "theo thời gian", "theo thoi gian", "thay đổi",
    "thay doi", "trend", "over time", "change", "longitudinal", "progress",
    "diễn biến", "dien bien", "tăng", "tang", "giảm", "giam",
]

DISTRIBUTION_KEYWORDS = [
    "phân phối", "phan phoi", "histogram", "spread", "distribution",
    "phân bố", "phan bo", "tần suất", "tan suat", "frequency",
    "mật độ", "mat do", "density",
]

CORRELATION_KEYWORDS = [
    "tương quan", "tuong quan", "liên quan", "lien quan", "correlation",
    "mối quan hệ", "moi quan he", "relationship", "scatter", "heatmap",
    "ảnh hưởng", "anh huong",
]

SURVIVAL_KEYWORDS = [
    "survival", "sống sót", "song sot", "kaplan", "meier",
    "time-to-event", "mortality", "tử vong", "tu vong",
]

DEMOGRAPHICS_KEYWORDS = [
    "demographics", "dân số", "dan so", "population", "age distribution",
    "phân bố dân", "phan bo dan", "giới tính", "gioi tinh",
]


# ── Decision Engine ─────────────────────────────────────────────────

class VisualizationDecisionEngine:
    """Decides the optimal chart type based on data and user intent."""

    def decide(
        self,
        user_prompt: str,
        schema_columns: list,
        data_summary: dict = None,
    ) -> ChartConfig:
        """
        Main decision method.
        Returns a ChartConfig with optimal visualization settings.
        """
        prompt_lower = user_prompt.lower()

        # Classify columns by type
        numeric_cols = [c for c in schema_columns if c["dtype"] in ("int64", "float64")]
        categorical_cols = [c for c in schema_columns if c["dtype"] in ("categorical", "string")]
        time_cols = [c for c in schema_columns if c["medical_role"] == "time_variable"]
        grouping_cols = [c for c in schema_columns if c["medical_role"] == "grouping"]
        biomarker_cols = [c for c in schema_columns if c["medical_role"] == "biomarker"]
        outcome_cols = [c for c in schema_columns if c["medical_role"] == "outcome"]

        # Detect intent from keywords
        intent = self._detect_intent(prompt_lower)

        # Find mentioned columns in prompt
        mentioned_cols = self._find_mentioned_columns(prompt_lower, schema_columns)

        # Make decision based on intent
        if intent == "comparison":
            return self._decide_comparison(
                mentioned_cols, grouping_cols, numeric_cols, outcome_cols, biomarker_cols, schema_columns
            )
        elif intent == "trend":
            return self._decide_trend(
                mentioned_cols, time_cols, numeric_cols, grouping_cols, schema_columns
            )
        elif intent == "distribution":
            return self._decide_distribution(
                mentioned_cols, numeric_cols, schema_columns
            )
        elif intent == "correlation":
            return self._decide_correlation(
                mentioned_cols, numeric_cols, biomarker_cols, schema_columns
            )
        elif intent == "survival":
            return self._decide_survival(
                mentioned_cols, time_cols, outcome_cols, grouping_cols, schema_columns
            )
        elif intent == "demographics":
            return self._decide_demographics(
                mentioned_cols, categorical_cols, numeric_cols, schema_columns
            )
        else:
            # Default: EDA Dashboard
            return self._decide_eda_dashboard(numeric_cols, categorical_cols, schema_columns)

    def _detect_intent(self, prompt_lower: str) -> str:
        """Detect visualization intent from user prompt keywords."""
        intent_scores = {
            "comparison": sum(1 for kw in COMPARISON_KEYWORDS if kw in prompt_lower),
            "trend": sum(1 for kw in TREND_KEYWORDS if kw in prompt_lower),
            "distribution": sum(1 for kw in DISTRIBUTION_KEYWORDS if kw in prompt_lower),
            "correlation": sum(1 for kw in CORRELATION_KEYWORDS if kw in prompt_lower),
            "survival": sum(1 for kw in SURVIVAL_KEYWORDS if kw in prompt_lower),
            "demographics": sum(1 for kw in DEMOGRAPHICS_KEYWORDS if kw in prompt_lower),
        }

        best_intent = max(intent_scores, key=intent_scores.get)
        if intent_scores[best_intent] == 0:
            return "eda"  # No clear intent → EDA dashboard
        return best_intent

    def _find_mentioned_columns(self, prompt_lower: str, columns: list) -> list:
        """Find which columns are mentioned in the user prompt."""
        mentioned = []
        for col in columns:
            col_name_lower = col["name"].lower()
            if col_name_lower in prompt_lower or col_name_lower.replace("_", " ") in prompt_lower:
                mentioned.append(col)
        return mentioned

    # ── Decision Methods per Intent ──────────────────────────────

    def _decide_comparison(self, mentioned, grouping_cols, numeric_cols, outcome_cols, biomarker_cols, all_cols):
        """Decide chart for comparison intent."""
        # Pick grouping variable
        group_col = None
        for col in mentioned:
            if col["medical_role"] == "grouping":
                group_col = col
                break
        if not group_col and grouping_cols:
            group_col = grouping_cols[0]

        # Pick outcome variable
        outcome_col = None
        for col in mentioned:
            if col["dtype"] in ("int64", "float64"):
                outcome_col = col
                break
        if not outcome_col and outcome_cols:
            outcome_col = outcome_cols[0]
        if not outcome_col and biomarker_cols:
            outcome_col = biomarker_cols[0]
        if not outcome_col and numeric_cols:
            outcome_col = numeric_cols[0]

        if not group_col or not outcome_col:
            return self._decide_eda_dashboard(numeric_cols, [], all_cols)

        # Determine number of groups
        n_groups = group_col.get("unique_count", 2)

        if n_groups == 2:
            chart_type = "box_strip_plot"
            annotations = ["mann_whitney_pvalue", "sample_size", "effect_size"]
        elif n_groups <= 5:
            chart_type = "violin_plot"
            annotations = ["kruskal_wallis_pvalue", "sample_size"]
        else:
            chart_type = "box_plot"
            annotations = ["sample_size"]

        return ChartConfig(
            chart_type=chart_type,
            library="seaborn",
            x_axis=group_col["name"],
            y_axis=outcome_col["name"],
            color_palette="treatment_control" if n_groups == 2 else "colorblind_safe",
            statistical_annotations=annotations,
            title=f"{outcome_col['name']} theo {group_col['name']}",
            xlabel=group_col["name"],
            ylabel=outcome_col["name"],
        )

    def _decide_trend(self, mentioned, time_cols, numeric_cols, grouping_cols, all_cols):
        """Decide chart for trend intent."""
        time_col = None
        for col in mentioned:
            if col["medical_role"] == "time_variable":
                time_col = col
                break
        if not time_col and time_cols:
            time_col = time_cols[0]

        outcome_col = None
        for col in mentioned:
            if col["dtype"] in ("int64", "float64"):
                outcome_col = col
                break
        if not outcome_col and numeric_cols:
            outcome_col = numeric_cols[0]

        if not time_col or not outcome_col:
            return self._decide_eda_dashboard(numeric_cols, [], all_cols)

        group_col = grouping_cols[0] if grouping_cols else None

        return ChartConfig(
            chart_type="line_chart",
            library="matplotlib",
            x_axis=time_col["name"],
            y_axis=outcome_col["name"],
            hue=group_col["name"] if group_col else None,
            color_palette="colorblind_safe",
            statistical_annotations=["confidence_band"],
            title=f"Xu hướng {outcome_col['name']} theo {time_col['name']}",
            xlabel=time_col["name"],
            ylabel=outcome_col["name"],
        )

    def _decide_distribution(self, mentioned, numeric_cols, all_cols):
        """Decide chart for distribution intent."""
        target_col = None
        for col in mentioned:
            if col["dtype"] in ("int64", "float64"):
                target_col = col
                break
        if not target_col and numeric_cols:
            target_col = numeric_cols[0]

        if not target_col:
            return self._decide_eda_dashboard(numeric_cols, [], all_cols)

        return ChartConfig(
            chart_type="histogram_kde",
            library="seaborn",
            x_axis=target_col["name"],
            color_palette="colorblind_safe",
            statistical_annotations=["normality_test", "descriptive_stats"],
            title=f"Phân phối {target_col['name']}",
            xlabel=target_col["name"],
            ylabel="Frequency / Density",
        )

    def _decide_correlation(self, mentioned, numeric_cols, biomarker_cols, all_cols):
        """Decide chart for correlation intent."""
        # If many numeric columns → heatmap
        relevant_numeric = [c for c in mentioned if c["dtype"] in ("int64", "float64")]
        if not relevant_numeric:
            relevant_numeric = biomarker_cols if biomarker_cols else numeric_cols

        if len(relevant_numeric) >= 3:
            col_names = [c["name"] for c in relevant_numeric[:15]]  # Max 15 for readability
            return ChartConfig(
                chart_type="correlation_heatmap",
                library="seaborn",
                color_palette="heatmap",
                statistical_annotations=["correlation_values", "significance_markers"],
                title="Ma trận tương quan",
                extra_params={"columns": col_names, "method": "spearman"},
            )
        elif len(relevant_numeric) == 2:
            return ChartConfig(
                chart_type="scatter_regression",
                library="seaborn",
                x_axis=relevant_numeric[0]["name"],
                y_axis=relevant_numeric[1]["name"],
                color_palette="colorblind_safe",
                statistical_annotations=["regression_line", "r_squared", "p_value"],
                title=f"Tương quan {relevant_numeric[0]['name']} vs {relevant_numeric[1]['name']}",
                xlabel=relevant_numeric[0]["name"],
                ylabel=relevant_numeric[1]["name"],
            )
        else:
            return self._decide_eda_dashboard(numeric_cols, [], all_cols)

    def _decide_survival(self, mentioned, time_cols, outcome_cols, grouping_cols, all_cols):
        """Decide chart for survival analysis."""
        time_col = time_cols[0] if time_cols else None
        outcome_col = outcome_cols[0] if outcome_cols else None
        group_col = grouping_cols[0] if grouping_cols else None

        if time_col and outcome_col:
            return ChartConfig(
                chart_type="kaplan_meier",
                library="lifelines",
                x_axis=time_col["name"],
                y_axis=outcome_col["name"],
                hue=group_col["name"] if group_col else None,
                color_palette="colorblind_safe",
                statistical_annotations=["log_rank_test", "median_survival", "confidence_band"],
                title="Đường cong sống sót Kaplan-Meier",
                xlabel="Thời gian",
                ylabel="Xác suất sống sót",
            )
        return self._decide_eda_dashboard([], [], all_cols)

    def _decide_demographics(self, mentioned, categorical_cols, numeric_cols, all_cols):
        """Decide chart for demographics intent."""
        # Find age and gender columns
        age_col = None
        gender_col = None
        for col in all_cols:
            name_lower = col["name"].lower()
            if "age" in name_lower or "tuoi" in name_lower:
                age_col = col
            if any(g in name_lower for g in ["gender", "sex", "gioi"]):
                gender_col = col

        if age_col and gender_col:
            return ChartConfig(
                chart_type="population_pyramid",
                library="matplotlib",
                x_axis=age_col["name"],
                hue=gender_col["name"],
                color_palette="treatment_control",
                title="Phân bố dân số theo tuổi và giới tính",
                xlabel="Số lượng",
                ylabel="Nhóm tuổi",
            )
        elif age_col:
            return ChartConfig(
                chart_type="histogram_kde",
                library="seaborn",
                x_axis=age_col["name"],
                color_palette="colorblind_safe",
                title=f"Phân phối {age_col['name']}",
                xlabel=age_col["name"],
                ylabel="Frequency",
            )
        return self._decide_eda_dashboard(numeric_cols, categorical_cols, all_cols)

    def _decide_eda_dashboard(self, numeric_cols, categorical_cols, all_cols):
        """Fallback: EDA dashboard with multiple small charts."""
        num_names = [c["name"] for c in numeric_cols[:6]] if numeric_cols else []
        cat_names = [c["name"] for c in categorical_cols[:3]] if categorical_cols else []

        return ChartConfig(
            chart_type="eda_dashboard",
            library="seaborn",
            color_palette="colorblind_safe",
            title="Exploratory Data Analysis Dashboard",
            extra_params={
                "numeric_columns": num_names,
                "categorical_columns": cat_names,
            },
        )
