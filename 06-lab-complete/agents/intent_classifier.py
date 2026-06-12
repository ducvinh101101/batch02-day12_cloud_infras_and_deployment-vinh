"""
Intent Classifier — Rule-based classification of user intent.
Fast keyword matching without needing an LLM call.
"""

from enum import Enum
import re


class UserIntent(Enum):
    ANALYZE_NEW = "analyze_new"         # Upload & analyze new CSV
    CREATE_CHART = "create_chart"       # Create a new visualization
    MODIFY_CHART = "modify_chart"       # Edit existing chart
    EXPLAIN_INSIGHT = "explain_insight" # Explain data or chart
    EXPORT = "export"                   # Download/export
    COMPARE_VERSIONS = "compare"        # Compare chart versions
    GENERAL_QUESTION = "general"        # General question about data


# Keyword patterns for each intent
MODIFY_PATTERNS = [
    r"đổi|thay đổi|thay doi|chuyển|chuyen|sửa|sua|chỉnh|chinh|edit|change|modify",
    r"thêm|them|add|bớt|bot|remove|xóa|xoa|delete",
    r"tăng|tang|giảm|giam|increase|decrease",
    r"màu|mau|color|font|size|kích thước|kich thuoc",
    r"error bar|annotation|legend|title|label",
    r"sang|thành|thanh|to\b|into",
]

EXPORT_PATTERNS = [
    r"tải|tai|download|export|xuất|xuat|save|lưu|luu",
    r"png|svg|pdf|html|code|mã nguồn|ma nguon",
]

EXPLAIN_PATTERNS = [
    r"giải thích|giai thich|explain|ý nghĩa|y nghia|meaning",
    r"tại sao|tai sao|why|lý do|ly do|reason",
    r"có nghĩa|co nghia|means|cho biết|cho biet|tell me",
    r"nhận xét|nhan xet|comment|phân tích|phan tich kết quả",
]

COMPARE_PATTERNS = [
    r"so sánh.*version|so sanh.*phiên bản|compare.*version",
    r"biểu đồ trước|bieu do truoc|previous chart|trước đó|truoc do",
]

CHART_KEYWORDS = [
    r"biểu đồ|bieu do|chart|graph|plot|vẽ|ve|draw|tạo|tao|create|visuali",
    r"histogram|scatter|bar|line|box|violin|heatmap|pie|dashboard",
    r"phân phối|phan phoi|distribution|xu hướng|xu huong|trend",
    r"tương quan|tuong quan|correlation|so sánh|so sanh|compare",
    r"kaplan|meier|roc|forest|bland|altman|survival|sống sót|song sot",
]


def classify_intent(
    prompt: str,
    has_active_chart: bool = False,
    has_active_dataset: bool = False,
) -> UserIntent:
    """
    Classify user intent from their prompt text.
    Uses rule-based keyword matching for speed.

    Args:
        prompt: User's message text
        has_active_chart: Whether there's a current chart in the session
        has_active_dataset: Whether there's an active dataset loaded

    Returns:
        UserIntent enum value
    """
    prompt_lower = prompt.lower().strip()

    # 1. Check for export intent
    if _matches_any(prompt_lower, EXPORT_PATTERNS):
        return UserIntent.EXPORT

    # 2. Check for chart comparison
    if _matches_any(prompt_lower, COMPARE_PATTERNS):
        return UserIntent.COMPARE_VERSIONS

    # 3. Check for modification (only if there's an active chart)
    if has_active_chart and _matches_any(prompt_lower, MODIFY_PATTERNS):
        # If they mention creating something new, it's not a modification
        if not re.search(r"(mới|moi|new|khác|khac|another)", prompt_lower):
            return UserIntent.MODIFY_CHART

    # 4. Check for explanation
    if _matches_any(prompt_lower, EXPLAIN_PATTERNS):
        return UserIntent.EXPLAIN_INSIGHT

    # 5. Check for chart creation
    if _matches_any(prompt_lower, CHART_KEYWORDS):
        return UserIntent.CREATE_CHART

    # 6. If dataset is loaded but no specific intent → likely wants a chart
    if has_active_dataset and not has_active_chart:
        return UserIntent.CREATE_CHART

    # 7. Default
    if has_active_dataset:
        return UserIntent.CREATE_CHART
    
    return UserIntent.GENERAL_QUESTION


def _matches_any(text: str, patterns: list) -> bool:
    """Check if text matches any of the regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False
