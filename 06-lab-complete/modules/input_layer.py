"""
Input Layer — CSV Parser, Validator, and Medical Role Classifier.
Handles file encoding detection, delimiter detection, schema inference,
PII scanning, and medical domain column classification.
"""

import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

import chardet
import pandas as pd
import numpy as np


# ── Data Classes ────────────────────────────────────────────────────

@dataclass
class ColumnInfo:
    """Metadata for a single CSV column."""
    name: str
    dtype: str
    null_rate: float
    medical_role: str  # identifier, demographic, biomarker, outcome, time_variable, grouping, confounding, unknown
    unique_count: int
    sample_values: list = field(default_factory=list)


@dataclass
class DataSchema:
    """Complete schema of a parsed CSV file."""
    file_id: str
    filename: str
    row_count: int
    col_count: int
    columns: list  # list of ColumnInfo dicts
    warnings: list = field(default_factory=list)
    encoding: str = "utf-8"
    delimiter: str = ","
    pii_detected: bool = False

    def to_dict(self):
        return asdict(self)

    def summary_text(self) -> str:
        """Human-readable summary for LLM context."""
        lines = [
            f"📄 File: {self.filename} ({self.row_count} rows × {self.col_count} columns)",
            f"   Encoding: {self.encoding}, Delimiter: '{self.delimiter}'",
            "",
            "📋 Columns:",
        ]
        for col in self.columns:
            c = col if isinstance(col, dict) else asdict(col)
            role_emoji = {
                "identifier": "🔑", "demographic": "👤", "biomarker": "🧬",
                "outcome": "🎯", "time_variable": "⏰", "grouping": "📊",
                "confounding": "⚙️", "unknown": "❓",
            }.get(c["medical_role"], "❓")
            null_pct = f"{c['null_rate']*100:.1f}%" if c["null_rate"] > 0 else "0%"
            sample_str = f", ví dụ: {c['sample_values'][:3]}" if c.get('sample_values') else ""
            lines.append(
                f"   {role_emoji} {c['name']} ({c['dtype']}) — role: {c['medical_role']}, "
                f"nulls: {null_pct}, unique: {c['unique_count']}{sample_str}"
            )
        if self.warnings:
            lines.append("")
            lines.append("⚠️ Warnings:")
            for w in self.warnings:
                lines.append(f"   - {w}")
        return "\n".join(lines)


# ── Medical Role Keywords ──────────────────────────────────────────

IDENTIFIER_PATTERNS = [
    r"patient.?id", r"subject.?id", r"^id$", r"record.?id", r"case.?id",
    r"mrn", r"medical.?record", r"enrollment",
]

DEMOGRAPHIC_PATTERNS = [
    r"^age", r"gender", r"sex", r"race", r"ethnicity", r"height", r"weight",
    r"bmi", r"body.?mass", r"education", r"income", r"occupation",
    r"marital", r"smoking", r"alcohol", r"tuoi", r"gioi.?tinh",
]

BIOMARKER_PATTERNS = [
    r"hba1c", r"glucose", r"cholesterol", r"ldl", r"hdl", r"triglyceride",
    r"creatinine", r"albumin", r"hemoglobin", r"platelet", r"wbc", r"rbc",
    r"insulin", r"cortisol", r"tsh", r"t3", r"t4", r"crp", r"esr",
    r"ferritin", r"vitamin", r"calcium", r"potassium", r"sodium",
    r"bilirubin", r"alt", r"ast", r"ggt", r"alk.?phos", r"bnp",
    r"troponin", r"psa", r"cea", r"afp", r"ca.?125", r"ca.?19",
    r"biomarker", r"marker", r"lab.?value", r"chi.?so",
]

OUTCOME_PATTERNS = [
    r"outcome", r"result", r"response", r"endpoint", r"event",
    r"death", r"mortality", r"survival", r"remission", r"relapse",
    r"cure", r"improvement", r"score", r"grade", r"stage",
    r"ket.?qua", r"diem",
]

TIME_PATTERNS = [
    r"date", r"time", r"day", r"week", r"month", r"year", r"visit",
    r"follow.?up", r"baseline", r"duration", r"period", r"interval",
    r"ngay", r"thoi.?gian", r"tuan", r"thang",
]

GROUPING_PATTERNS = [
    r"group", r"arm", r"treatment", r"control", r"placebo", r"intervention",
    r"cohort", r"category", r"class", r"type", r"nhom", r"dieu.?tri",
    r"phan.?loai",
]

PII_PATTERNS = [
    r"(ho.?ten|full.?name|first.?name|last.?name)",
    r"(cmnd|cccd|passport|identity)",
    r"(phone|dien.?thoai|so.?dt)",
    r"(email|e.?mail)",
    r"(address|dia.?chi)",
    r"(insurance|bao.?hiem)",
]


# ── Main Parser ────────────────────────────────────────────────────

class MedicalCSVParser:
    """Parses CSV files with medical-domain awareness."""

    def parse(self, file_path: str, original_filename: str = "") -> DataSchema:
        """
        Parse a CSV file and return a DataSchema with medical role classification.
        """
        filename = original_filename or file_path.split("/")[-1].split("\\")[-1]

        # Step 1: Detect encoding
        encoding = self._detect_encoding(file_path)

        # Step 2: Detect delimiter
        delimiter = self._detect_delimiter(file_path, encoding)

        # Step 3: Load DataFrame
        df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)

        # Step 4: Build schema
        warnings = []
        columns = []

        for col_name in df.columns:
            series = df[col_name]
            dtype_str = self._simplify_dtype(series.dtype, series)
            null_rate = float(series.isnull().mean())
            unique_count = int(series.nunique())

            # Warn on high nulls
            if null_rate > 0.3:
                warnings.append(f"Column '{col_name}' has {null_rate*100:.1f}% missing values")

            # Get sample values (up to 5 non-null unique values)
            sample = series.dropna().unique()[:5].tolist()
            sample = [str(v) for v in sample]

            # Classify medical role
            medical_role = self._classify_medical_role(col_name, dtype_str, unique_count, df.shape[0])

            columns.append(ColumnInfo(
                name=col_name,
                dtype=dtype_str,
                null_rate=round(null_rate, 4),
                medical_role=medical_role,
                unique_count=unique_count,
                sample_values=sample,
            ))

        # Step 5: Validate
        validation_warnings = self._validate(df)
        warnings.extend(validation_warnings)

        # Step 6: PII check
        pii_detected = self._detect_pii(df)
        if pii_detected:
            warnings.append("⚠️ Potential PII (personally identifiable information) detected! Consider anonymizing data.")

        schema = DataSchema(
            file_id=str(uuid.uuid4()),
            filename=filename,
            row_count=df.shape[0],
            col_count=df.shape[1],
            columns=[asdict(c) for c in columns],
            warnings=warnings,
            encoding=encoding,
            delimiter=delimiter,
            pii_detected=pii_detected,
        )

        return schema

    def load_dataframe(self, file_path: str, encoding: str = "utf-8", delimiter: str = ",") -> pd.DataFrame:
        """Load the CSV as a pandas DataFrame."""
        return pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)

    # ── Private Methods ──────────────────────────────────────────

    def _detect_encoding(self, file_path: str) -> str:
        """Auto-detect file encoding using chardet."""
        with open(file_path, "rb") as f:
            raw = f.read(min(100000, f.seek(0, 2)))
            f.seek(0)
            raw = f.read(min(100000, len(raw) if raw else 100000))
        
        # Re-read properly
        with open(file_path, "rb") as f:
            raw = f.read(100000)

        result = chardet.detect(raw)
        encoding = result.get("encoding", "utf-8") or "utf-8"

        # Normalize common aliases
        encoding_map = {
            "ascii": "utf-8",
            "iso-8859-1": "latin-1",
            "windows-1252": "latin-1",
        }
        return encoding_map.get(encoding.lower(), encoding)

    def _detect_delimiter(self, file_path: str, encoding: str) -> str:
        """Detect CSV delimiter from first few lines."""
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            sample = ""
            for i, line in enumerate(f):
                sample += line
                if i >= 5:
                    break

        # Count occurrences of common delimiters
        delimiters = {",": 0, ";": 0, "\t": 0, "|": 0}
        for d in delimiters:
            delimiters[d] = sample.count(d)

        # Pick the most frequent
        best = max(delimiters, key=delimiters.get)
        return best if delimiters[best] > 0 else ","

    def _simplify_dtype(self, dtype, series: pd.Series) -> str:
        """Simplify pandas dtype to a human-readable string."""
        dtype_str = str(dtype)
        if "int" in dtype_str:
            return "int64"
        elif "float" in dtype_str:
            return "float64"
        elif "bool" in dtype_str:
            return "boolean"
        elif "datetime" in dtype_str:
            return "datetime"
        elif "object" in dtype_str:
            # Check if it looks categorical
            ratio = series.nunique() / max(len(series), 1)
            if ratio < 0.05 or series.nunique() <= 20:
                return "categorical"
            # Check if it's a date string
            try:
                pd.to_datetime(series.dropna().head(5))
                return "datetime_string"
            except (ValueError, TypeError):
                pass
            return "string"
        return dtype_str

    def _classify_medical_role(self, col_name: str, dtype: str, unique_count: int, total_rows: int) -> str:
        """Classify a column's medical role using keyword patterns."""
        name_lower = col_name.lower().strip()

        # Check each pattern category
        for pattern in IDENTIFIER_PATTERNS:
            if re.search(pattern, name_lower):
                return "identifier"

        for pattern in TIME_PATTERNS:
            if re.search(pattern, name_lower):
                return "time_variable"

        for pattern in GROUPING_PATTERNS:
            if re.search(pattern, name_lower):
                return "grouping"

        for pattern in BIOMARKER_PATTERNS:
            if re.search(pattern, name_lower):
                return "biomarker"

        for pattern in OUTCOME_PATTERNS:
            if re.search(pattern, name_lower):
                return "outcome"

        for pattern in DEMOGRAPHIC_PATTERNS:
            if re.search(pattern, name_lower):
                return "demographic"

        # Heuristic fallbacks
        if dtype in ("categorical", "string") and unique_count <= 10:
            return "grouping"
        if dtype in ("int64", "float64"):
            return "biomarker"  # Default numeric to biomarker in medical context

        return "unknown"

    def _validate(self, df: pd.DataFrame) -> list:
        """Validate basic requirements for analysis."""
        warnings = []
        if df.shape[1] < 2:
            warnings.append("Dataset has fewer than 2 columns — limited analysis possible")
        if df.shape[0] < 5:
            warnings.append("Dataset has fewer than 5 rows — results may be unreliable")
        if df.shape[0] < 10:
            warnings.append("Small sample size (n < 10) — statistical tests may lack power")
        return warnings

    def _detect_pii(self, df: pd.DataFrame) -> bool:
        """Scan column names for potential PII indicators."""
        all_cols = " ".join(df.columns.str.lower())
        for pattern in PII_PATTERNS:
            if re.search(pattern, all_cols):
                return True
        return False
