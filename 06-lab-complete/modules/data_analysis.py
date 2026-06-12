"""
Data Analysis Module — Statistical Analysis Engine & Medical Domain Classifier.
Computes descriptive statistics, normality tests, group comparisons,
and classifies the type of medical study from data structure.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

import pandas as pd
import numpy as np
from scipy import stats


# ── Data Classes ────────────────────────────────────────────────────

@dataclass
class ColumnStats:
    """Statistical summary for a single column."""
    name: str
    dtype: str
    stats: dict = field(default_factory=dict)


@dataclass
class MedicalContext:
    """Medical domain classification result."""
    study_type: str  # RCT, Cohort, Cross-sectional, Lab Results, Survival
    confidence: float
    key_variables: dict = field(default_factory=dict)  # {role: [col_names]}
    suggested_analyses: list = field(default_factory=list)

    def summary_text(self) -> str:
        lines = [
            f"🔬 Study Type: {self.study_type} (confidence: {self.confidence:.0%})",
            "",
            "📌 Key Variables:",
        ]
        for role, cols in self.key_variables.items():
            lines.append(f"   {role}: {', '.join(cols)}")
        if self.suggested_analyses:
            lines.append("")
            lines.append("💡 Suggested Analyses:")
            for a in self.suggested_analyses:
                lines.append(f"   - {a}")
        return "\n".join(lines)


@dataclass
class StatsReport:
    """Complete statistical report for a dataset."""
    column_stats: list  # list of ColumnStats dicts
    medical_context: dict  # MedicalContext dict
    data_summary: dict = field(default_factory=dict)  # shape, dtypes overview

    def summary_text(self) -> str:
        lines = ["📊 Statistical Summary:", ""]
        for cs in self.column_stats:
            c = cs if isinstance(cs, dict) else asdict(cs)
            lines.append(f"  📈 {c['name']} ({c['dtype']}):")
            for k, v in c["stats"].items():
                if isinstance(v, float):
                    lines.append(f"     {k}: {v:.4f}")
                elif isinstance(v, dict):
                    lines.append(f"     {k}: {v}")
                else:
                    lines.append(f"     {k}: {v}")
            lines.append("")
        return "\n".join(lines)


# ── Statistical Analysis Engine ─────────────────────────────────────

class StatisticalAnalyzer:
    """Computes comprehensive statistics for medical data."""

    def analyze(self, df: pd.DataFrame, schema_columns: list) -> StatsReport:
        """
        Analyze all columns and return a StatsReport.
        schema_columns: list of column info dicts from DataSchema
        """
        column_stats = []

        for col_info in schema_columns:
            col_name = col_info["name"]
            dtype = col_info["dtype"]

            if col_name not in df.columns:
                continue

            series = df[col_name]

            if dtype in ("int64", "float64"):
                col_stats = self._analyze_numeric(series, col_name)
            elif dtype in ("categorical", "string"):
                col_stats = self._analyze_categorical(series, col_name)
            elif dtype in ("boolean",):
                col_stats = self._analyze_binary(series, col_name)
            elif dtype in ("datetime", "datetime_string"):
                col_stats = self._analyze_temporal(series, col_name)
            else:
                col_stats = ColumnStats(name=col_name, dtype=dtype, stats={"note": "Type not analyzed"})

            column_stats.append(asdict(col_stats))

        # Classify medical domain
        medical_ctx = MedicalDomainClassifier().classify(schema_columns)

        # Data summary
        data_summary = {
            "rows": df.shape[0],
            "columns": df.shape[1],
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "total_nulls": int(df.isnull().sum().sum()),
            "null_percentage": round(df.isnull().mean().mean() * 100, 2),
        }

        return StatsReport(
            column_stats=column_stats,
            medical_context=asdict(medical_ctx),
            data_summary=data_summary,
        )

    def _analyze_numeric(self, series: pd.Series, name: str) -> ColumnStats:
        """Compute stats for numeric columns: mean, median, std, IQR, skewness, kurtosis, normality."""
        clean = series.dropna()
        if len(clean) < 3:
            return ColumnStats(name=name, dtype="numeric", stats={"n": len(clean), "note": "Too few values"})

        q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
        iqr = q3 - q1

        stats_dict = {
            "n": int(len(clean)),
            "mean": round(float(clean.mean()), 4),
            "median": round(float(clean.median()), 4),
            "std": round(float(clean.std()), 4),
            "min": round(float(clean.min()), 4),
            "max": round(float(clean.max()), 4),
            "q1": round(float(q1), 4),
            "q3": round(float(q3), 4),
            "iqr": round(float(iqr), 4),
            "skewness": round(float(clean.skew()), 4),
            "kurtosis": round(float(clean.kurtosis()), 4),
        }

        # Normality test (Shapiro-Wilk) — only for reasonable sample sizes
        if 3 <= len(clean) <= 5000:
            try:
                shapiro_stat, shapiro_p = stats.shapiro(clean.sample(min(len(clean), 5000)))
                stats_dict["normality_test"] = {
                    "test": "Shapiro-Wilk",
                    "statistic": round(float(shapiro_stat), 4),
                    "p_value": round(float(shapiro_p), 6),
                    "is_normal": bool(shapiro_p > 0.05),
                }
            except Exception:
                stats_dict["normality_test"] = {"test": "Shapiro-Wilk", "error": "Could not compute"}

        # Outlier count (using IQR method)
        if iqr > 0:
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            outliers = int(((clean < lower_fence) | (clean > upper_fence)).sum())
            stats_dict["outlier_count"] = outliers

        return ColumnStats(name=name, dtype="numeric", stats=stats_dict)

    def _analyze_categorical(self, series: pd.Series, name: str) -> ColumnStats:
        """Compute stats for categorical columns."""
        clean = series.dropna()
        freq = clean.value_counts()

        stats_dict = {
            "n": int(len(clean)),
            "unique_values": int(clean.nunique()),
            "mode": str(freq.index[0]) if len(freq) > 0 else None,
            "mode_frequency": int(freq.iloc[0]) if len(freq) > 0 else 0,
            "top_5_values": {str(k): int(v) for k, v in freq.head(5).items()},
        }

        # Chi-square readiness
        if clean.nunique() >= 2:
            stats_dict["chi_square_ready"] = True

        return ColumnStats(name=name, dtype="categorical", stats=stats_dict)

    def _analyze_binary(self, series: pd.Series, name: str) -> ColumnStats:
        """Compute stats for binary outcome columns."""
        clean = series.dropna()
        event_rate = float(clean.mean()) if clean.dtype == bool else float((clean == 1).mean())

        stats_dict = {
            "n": int(len(clean)),
            "event_rate": round(event_rate, 4),
            "event_count": int(clean.sum()),
            "non_event_count": int(len(clean) - clean.sum()),
        }
        return ColumnStats(name=name, dtype="binary", stats=stats_dict)

    def _analyze_temporal(self, series: pd.Series, name: str) -> ColumnStats:
        """Basic temporal column analysis."""
        try:
            dt_series = pd.to_datetime(series, errors="coerce")
            clean = dt_series.dropna()
            stats_dict = {
                "n": int(len(clean)),
                "min_date": str(clean.min()),
                "max_date": str(clean.max()),
                "span_days": int((clean.max() - clean.min()).days) if len(clean) > 1 else 0,
            }
        except Exception:
            stats_dict = {"n": int(series.notna().sum()), "note": "Could not parse as datetime"}
        return ColumnStats(name=name, dtype="temporal", stats=stats_dict)

    def compute_group_comparison(self, df: pd.DataFrame, grouping_col: str, outcome_col: str) -> dict:
        """Compute group comparison statistics (t-test or Mann-Whitney)."""
        groups = df.groupby(grouping_col)[outcome_col].apply(lambda x: x.dropna().values)
        group_names = list(groups.index)

        if len(group_names) < 2:
            return {"error": "Need at least 2 groups for comparison"}

        result = {
            "grouping_variable": grouping_col,
            "outcome_variable": outcome_col,
            "group_summaries": {},
        }

        for gname in group_names:
            vals = groups[gname]
            result["group_summaries"][str(gname)] = {
                "n": len(vals),
                "mean": round(float(np.mean(vals)), 4),
                "median": round(float(np.median(vals)), 4),
                "std": round(float(np.std(vals, ddof=1)), 4) if len(vals) > 1 else 0,
            }

        # Statistical test
        if len(group_names) == 2:
            g1, g2 = groups[group_names[0]], groups[group_names[1]]
            # Check normality to decide test
            try:
                _, p1 = stats.shapiro(g1[:5000]) if len(g1) >= 3 else (0, 0)
                _, p2 = stats.shapiro(g2[:5000]) if len(g2) >= 3 else (0, 0)
                both_normal = p1 > 0.05 and p2 > 0.05
            except Exception:
                both_normal = False

            if both_normal:
                stat_val, p_val = stats.ttest_ind(g1, g2)
                test_name = "Independent t-test"
            else:
                stat_val, p_val = stats.mannwhitneyu(g1, g2, alternative="two-sided")
                test_name = "Mann-Whitney U"

            result["test"] = {
                "name": test_name,
                "statistic": round(float(stat_val), 4),
                "p_value": round(float(p_val), 6),
                "significant": bool(p_val < 0.05),
            }
        elif len(group_names) >= 3:
            # ANOVA or Kruskal-Wallis
            all_groups = [groups[g] for g in group_names]
            try:
                stat_val, p_val = stats.kruskal(*all_groups)
                result["test"] = {
                    "name": "Kruskal-Wallis H",
                    "statistic": round(float(stat_val), 4),
                    "p_value": round(float(p_val), 6),
                    "significant": bool(p_val < 0.05),
                }
            except Exception:
                result["test"] = {"error": "Could not compute test"}

        return result


# ── Medical Domain Classifier ──────────────────────────────────────

class MedicalDomainClassifier:
    """Classifies the type of medical study from data structure."""

    def classify(self, schema_columns: list) -> MedicalContext:
        """Classify study type from column metadata."""
        roles = {}
        for col in schema_columns:
            role = col["medical_role"]
            if role not in roles:
                roles[role] = []
            roles[role].append(col["name"])

        has_grouping = "grouping" in roles
        has_outcome = "outcome" in roles
        has_time = "time_variable" in roles
        has_biomarker = "biomarker" in roles

        # Decision logic
        if has_grouping and has_outcome and has_time:
            study_type = "RCT (Randomized Controlled Trial)"
            confidence = 0.85
            suggestions = [
                "Compare outcomes between treatment groups over time",
                "Kaplan-Meier survival analysis (if time-to-event data)",
                "Longitudinal trend analysis by group",
                "Effect size calculation (Cohen's d)",
            ]
        elif has_grouping and has_outcome:
            study_type = "Controlled Study"
            confidence = 0.7
            suggestions = [
                "Compare outcomes between groups (box/violin plot)",
                "Statistical tests (t-test / Mann-Whitney)",
                "Effect size and confidence intervals",
            ]
        elif has_time and has_outcome:
            study_type = "Cohort Study"
            confidence = 0.65
            suggestions = [
                "Survival analysis (Kaplan-Meier)",
                "Time-series trend analysis",
                "Cox regression (if time-to-event)",
            ]
        elif has_biomarker and len(roles.get("biomarker", [])) >= 3:
            study_type = "Lab Results / Biomarker Panel"
            confidence = 0.75
            suggestions = [
                "Correlation heatmap between biomarkers",
                "Distribution analysis for each biomarker",
                "Reference range comparison",
                "Outlier detection",
            ]
        elif has_time:
            study_type = "Longitudinal Study"
            confidence = 0.5
            suggestions = [
                "Trend analysis over time",
                "Seasonal pattern detection",
            ]
        else:
            study_type = "Cross-sectional Study"
            confidence = 0.4
            suggestions = [
                "Exploratory Data Analysis (EDA) dashboard",
                "Distribution analysis for key variables",
                "Correlation analysis",
                "Demographic breakdown",
            ]

        return MedicalContext(
            study_type=study_type,
            confidence=confidence,
            key_variables=roles,
            suggested_analyses=suggestions,
        )
