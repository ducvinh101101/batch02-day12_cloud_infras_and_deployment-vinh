"""Medical Research Agent configuration loaded from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "outputs"))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
STATIC_DIR = BASE_DIR / "static"

for directory in (UPLOAD_DIR, OUTPUT_DIR, DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
EXECUTION_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "60"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DATABASE_PATH = DATA_DIR / "memory.db"

ALLOWED_IMPORTS = {
    "pandas", "numpy", "matplotlib", "matplotlib.pyplot", "matplotlib.patches",
    "matplotlib.ticker", "matplotlib.gridspec", "matplotlib.colors",
    "seaborn", "plotly", "plotly.express", "plotly.graph_objects",
    "plotly.subplots", "scipy", "scipy.stats", "lifelines",
    "lifelines.KaplanMeierFitter", "lifelines.statistics",
    "sklearn", "sklearn.metrics", "statsmodels", "statsmodels.api",
    "statsmodels.stats", "math", "statistics", "datetime", "json",
    "os.path", "warnings", "textwrap", "io",
}

BLOCKED_PATTERNS = [
    "os.system", "subprocess", "eval(", "exec(", "__import__",
    "socket", "requests", "urllib", "http.client", "shutil.rmtree",
    "open(", "pathlib",
]

MEDICAL_PALETTES = {
    "treatment_control": ["#2196F3", "#FF5722"],
    "severity": ["#4CAF50", "#FFC107", "#F44336"],
    "colorblind_safe": ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9"],
    "grayscale_print": ["#333333", "#777777", "#BBBBBB"],
    "heatmap": "RdYlGn_r",
    "default": ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9", "#E69F00"],
}
