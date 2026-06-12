"""
Chart Templates — Complete Python code templates for various
medical visualization types.

Each template uses placeholders:
  {{DATA_PATH}}, {{OUTPUT_PATH}}, {{X_AXIS}}, {{Y_AXIS}},
  {{HUE}}, {{TITLE}}, {{XLABEL}}, {{YLABEL}}, {{PALETTE}},
  {{FIGSIZE_W}}, {{FIGSIZE_H}}, {{DPI}}, {{COLUMNS}},
  {{NUMERIC_COLUMNS}}, {{CATEGORICAL_COLUMNS}}, {{METHOD}}
"""

CHART_TEMPLATES = {}

# ════════════════════════════════════════════════════════════════
# 1. BOX + STRIP PLOT (2-group comparison)
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["box_strip_plot"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# ── Configuration ──────────────────────────────────────────────
plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}
plt.rcParams['font.size'] = 12

# ── Data Loading ───────────────────────────────────────────────
df = pd.read_csv({{DATA_PATH}})
df = df.dropna(subset=["{{X_AXIS}}", "{{Y_AXIS}}"])
print(f"Loaded: {df.shape[0]} rows after dropping nulls")

# ── Statistical Test ───────────────────────────────────────────
groups = df.groupby("{{X_AXIS}}")["{{Y_AXIS}}"].apply(list)
group_names = list(groups.index)
if len(group_names) >= 2:
    g1, g2 = np.array(groups.iloc[0]), np.array(groups.iloc[1])
    stat_val, p_value = stats.mannwhitneyu(g1, g2, alternative='two-sided')
    # Effect size (rank-biserial correlation)
    n1, n2 = len(g1), len(g2)
    effect_size = 1 - (2 * stat_val) / (n1 * n2)
else:
    p_value = None
    effect_size = None

# ── Visualization ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

# Box plot
sns.boxplot(data=df, x="{{X_AXIS}}", y="{{Y_AXIS}}",
            palette=PALETTE, width=0.5, linewidth=1.5,
            fliersize=0, ax=ax)

# Strip plot overlay
sns.stripplot(data=df, x="{{X_AXIS}}", y="{{Y_AXIS}}",
              palette=PALETTE, size=4, alpha=0.4,
              jitter=0.2, ax=ax)

# ── Annotations ────────────────────────────────────────────────
if p_value is not None:
    significance = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
    y_max = df["{{Y_AXIS}}"].max()
    y_range = df["{{Y_AXIS}}"].max() - df["{{Y_AXIS}}"].min()
    bracket_height = y_max + y_range * 0.05
    bar_height = y_range * 0.02

    ax.plot([0, 0, 1, 1],
            [bracket_height, bracket_height + bar_height, bracket_height + bar_height, bracket_height],
            lw=1.5, c='black')
    ax.text(0.5, bracket_height + bar_height * 1.5,
            f'{significance}\\np = {p_value:.4f} (Mann-Whitney U)',
            ha='center', va='bottom', fontsize=11)

# Sample sizes
for i, gname in enumerate(group_names[:2]):
    n = len(groups.iloc[i])
    ax.text(i, df["{{Y_AXIS}}"].min() - y_range * 0.08,
            f'n = {n}', ha='center', va='top', fontsize=10, style='italic')

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)
ax.tick_params(axis='both', labelsize=11)

# ── Export ─────────────────────────────────────────────────────
plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print(f"Chart saved. p-value = {p_value}, effect_size = {effect_size}")
'''

# ════════════════════════════════════════════════════════════════
# 2. VIOLIN PLOT (multi-group comparison)
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["violin_plot"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
df = df.dropna(subset=["{{X_AXIS}}", "{{Y_AXIS}}"])

# ── Statistical Test (Kruskal-Wallis) ──────────────────────────
groups = [group["{{Y_AXIS}}"].values for name, group in df.groupby("{{X_AXIS}}")]
if len(groups) >= 2:
    h_stat, p_value = stats.kruskal(*groups)
else:
    h_stat, p_value = None, None

# ── Visualization ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

sns.violinplot(data=df, x="{{X_AXIS}}", y="{{Y_AXIS}}",
               palette=PALETTE, inner="box", linewidth=1.2, ax=ax)
sns.stripplot(data=df, x="{{X_AXIS}}", y="{{Y_AXIS}}",
              color="black", size=3, alpha=0.3, jitter=0.15, ax=ax)

# Annotations
if p_value is not None:
    sig_text = f"Kruskal-Wallis H = {h_stat:.2f}, p = {p_value:.4f}"
    if p_value < 0.05:
        sig_text += " ✓ Significant"
    else:
        sig_text += " (Not significant)"
    ax.text(0.98, 0.98, sig_text, transform=ax.transAxes,
            ha='right', va='top', fontsize=10,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))

# Sample sizes
for i, (name, group) in enumerate(df.groupby("{{X_AXIS}}")):
    ax.text(i, ax.get_ylim()[0], f'n={len(group)}',
            ha='center', va='top', fontsize=10, style='italic')

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print(f"Violin plot saved. Kruskal-Wallis p = {p_value}")
'''

# ════════════════════════════════════════════════════════════════
# 3. BOX PLOT (general)
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["box_plot"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
df = df.dropna(subset=["{{X_AXIS}}", "{{Y_AXIS}}"])

fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})
sns.boxplot(data=df, x="{{X_AXIS}}", y="{{Y_AXIS}}", palette=PALETTE, ax=ax)

for i, (name, group) in enumerate(df.groupby("{{X_AXIS}}")):
    ax.text(i, ax.get_ylim()[0], f'n={len(group)}',
            ha='center', va='top', fontsize=10, style='italic')

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print("Box plot saved.")
'''

# ════════════════════════════════════════════════════════════════
# 4. LINE CHART (trend over time)
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["line_chart"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
df = df.dropna(subset=["{{X_AXIS}}", "{{Y_AXIS}}"])

# Try to sort by time axis
try:
    df["{{X_AXIS}}"] = pd.to_datetime(df["{{X_AXIS}}"])
except (ValueError, TypeError):
    pass
df = df.sort_values("{{X_AXIS}}")

fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

hue_col = "{{HUE}}"
if hue_col and hue_col in df.columns:
    for i, (name, group) in enumerate(df.groupby(hue_col)):
        color = PALETTE[i % len(PALETTE)] if isinstance(PALETTE, list) else None
        ax.plot(group["{{X_AXIS}}"], group["{{Y_AXIS}}"],
                marker='o', markersize=4, label=str(name), color=color, linewidth=2)
    ax.legend(title=hue_col, fontsize=10)
else:
    ax.plot(df["{{X_AXIS}}"], df["{{Y_AXIS}}"],
            marker='o', markersize=4, color=PALETTE[0] if isinstance(PALETTE, list) else '#0072B2',
            linewidth=2)

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)
plt.xticks(rotation=45, ha='right')

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print("Line chart saved.")
'''

# ════════════════════════════════════════════════════════════════
# 5. HISTOGRAM + KDE (distribution)
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["histogram_kde"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
col = "{{X_AXIS}}"
data = df[col].dropna()

# ── Statistics ─────────────────────────────────────────────────
mean_val = data.mean()
median_val = data.median()
std_val = data.std()
skew_val = data.skew()

# Normality test
if len(data) >= 3:
    shapiro_stat, shapiro_p = stats.shapiro(data.sample(min(len(data), 5000)))
else:
    shapiro_stat, shapiro_p = None, None

# ── Visualization ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

color = PALETTE[0] if isinstance(PALETTE, list) else '#0072B2'

sns.histplot(data=data, kde=True, color=color, alpha=0.6,
             edgecolor='white', linewidth=0.5, ax=ax)

# Add mean and median lines
ax.axvline(mean_val, color='#E74C3C', linestyle='--', linewidth=2, label=f'Mean = {mean_val:.2f}')
ax.axvline(median_val, color='#2ECC71', linestyle='-.', linewidth=2, label=f'Median = {median_val:.2f}')

# Stats box
stats_text = (
    f"n = {len(data)}\\n"
    f"Mean = {mean_val:.3f}\\n"
    f"Median = {median_val:.3f}\\n"
    f"SD = {std_val:.3f}\\n"
    f"Skewness = {skew_val:.3f}"
)
if shapiro_p is not None:
    stats_text += f"\\nShapiro p = {shapiro_p:.4f}"
    stats_text += f"\\n{'Normal ✓' if shapiro_p > 0.05 else 'Non-normal ✗'}"

ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
        ha='right', va='top', fontsize=10, family='monospace',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.9))

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print(f"Histogram saved. Mean={mean_val:.3f}, Median={median_val:.3f}")
'''

# ════════════════════════════════════════════════════════════════
# 6. SCATTER + REGRESSION (correlation, 2 variables)
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["scatter_regression"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
df = df.dropna(subset=["{{X_AXIS}}", "{{Y_AXIS}}"])

x = df["{{X_AXIS}}"]
y = df["{{Y_AXIS}}"]

# ── Statistics ─────────────────────────────────────────────────
r_val, p_val = stats.pearsonr(x, y)
rho_val, rho_p = stats.spearmanr(x, y)
slope, intercept, _, _, std_err = stats.linregress(x, y)

# ── Visualization ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

color = PALETTE[0] if isinstance(PALETTE, list) else '#0072B2'
sns.regplot(data=df, x="{{X_AXIS}}", y="{{Y_AXIS}}",
            scatter_kws={'alpha': 0.5, 's': 40, 'color': color},
            line_kws={'color': '#E74C3C', 'linewidth': 2},
            ci=95, ax=ax)

# Stats annotation
stats_text = (
    f"Pearson r = {r_val:.3f} (p = {p_val:.4f})\\n"
    f"Spearman ρ = {rho_val:.3f} (p = {rho_p:.4f})\\n"
    f"R² = {r_val**2:.3f}\\n"
    f"y = {slope:.3f}x + {intercept:.3f}\\n"
    f"n = {len(x)}"
)

ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
        ha='left', va='top', fontsize=10, family='monospace',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.9))

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print(f"Scatter plot saved. Pearson r = {r_val:.3f}, p = {p_val:.4f}")
'''

# ════════════════════════════════════════════════════════════════
# 7. CORRELATION HEATMAP
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["correlation_heatmap"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')

df = pd.read_csv({{DATA_PATH}})

# Select numeric columns
columns = {{COLUMNS}} if {{COLUMNS}} else df.select_dtypes(include=[np.number]).columns.tolist()
df_numeric = df[columns].dropna()

# Compute correlation matrix
method = "{{METHOD}}" if "{{METHOD}}" else "spearman"
corr_matrix = df_numeric.corr(method=method)

# ── Visualization ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)

sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f',
            cmap='RdYlGn_r', center=0, vmin=-1, vmax=1,
            square=True, linewidths=0.5, linecolor='white',
            cbar_kws={'shrink': 0.8, 'label': f'{method.capitalize()} Correlation'},
            ax=ax)

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
plt.xticks(rotation=45, ha='right', fontsize=10)
plt.yticks(fontsize=10)

# Find strongest correlations
corr_pairs = []
for i in range(len(corr_matrix.columns)):
    for j in range(i+1, len(corr_matrix.columns)):
        corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j],
                          corr_matrix.iloc[i, j]))
corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

print(f"Top correlations ({method}):")
for c1, c2, r in corr_pairs[:5]:
    print(f"  {c1} ↔ {c2}: r = {r:.3f}")

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print("Correlation heatmap saved.")
'''

# ════════════════════════════════════════════════════════════════
# 8. KAPLAN-MEIER SURVIVAL CURVE
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["kaplan_meier"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
time_col = "{{X_AXIS}}"
event_col = "{{Y_AXIS}}"

df = df.dropna(subset=[time_col, event_col])

fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

hue_col = "{{HUE}}"
if hue_col and hue_col in df.columns:
    groups = df[hue_col].unique()
    kmfs = []
    for i, group in enumerate(groups):
        mask = df[hue_col] == group
        kmf = KaplanMeierFitter()
        color = PALETTE[i % len(PALETTE)] if isinstance(PALETTE, list) else None
        kmf.fit(df.loc[mask, time_col], event_observed=df.loc[mask, event_col], label=str(group))
        kmf.plot_survival_function(ax=ax, color=color, linewidth=2)
        kmfs.append((group, mask))

    # Log-rank test for 2 groups
    if len(groups) == 2:
        m1 = df[hue_col] == groups[0]
        m2 = df[hue_col] == groups[1]
        result = logrank_test(df.loc[m1, time_col], df.loc[m2, time_col],
                             event_observed_A=df.loc[m1, event_col],
                             event_observed_B=df.loc[m2, event_col])
        ax.text(0.98, 0.02, f'Log-rank p = {result.p_value:.4f}',
                transform=ax.transAxes, ha='right', va='bottom', fontsize=11,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
else:
    kmf = KaplanMeierFitter()
    kmf.fit(df[time_col], event_observed=df[event_col])
    kmf.plot_survival_function(ax=ax, color=PALETTE[0] if isinstance(PALETTE, list) else '#0072B2',
                                linewidth=2)

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)
ax.set_ylim(0, 1.05)

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print("Kaplan-Meier curve saved.")
'''

# ════════════════════════════════════════════════════════════════
# 9. EDA DASHBOARD (fallback — multiple small charts)
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["eda_dashboard"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})

# Select columns
numeric_cols = {{NUMERIC_COLUMNS}} if {{NUMERIC_COLUMNS}} else df.select_dtypes(include=[np.number]).columns.tolist()[:6]
categorical_cols = {{CATEGORICAL_COLUMNS}} if {{CATEGORICAL_COLUMNS}} else df.select_dtypes(include=['object', 'category']).columns.tolist()[:3]

n_numeric = min(len(numeric_cols), 6)
n_categorical = min(len(categorical_cols), 3)
total_plots = n_numeric + n_categorical

if total_plots == 0:
    print("No columns to plot!")
else:
    # Calculate grid
    ncols = 3
    nrows = (total_plots + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(6*ncols, 5*nrows), dpi={{DPI}})
    if nrows == 1 and ncols == 1:
        axes = np.array([[axes]])
    elif nrows == 1:
        axes = axes.reshape(1, -1)
    elif ncols == 1:
        axes = axes.reshape(-1, 1)

    plot_idx = 0

    # Numeric distributions
    for i, col in enumerate(numeric_cols[:n_numeric]):
        row, col_idx = divmod(plot_idx, ncols)
        ax = axes[row][col_idx]
        color = PALETTE[i % len(PALETTE)] if isinstance(PALETTE, list) else '#0072B2'
        sns.histplot(data=df, x=col, kde=True, color=color, alpha=0.6, ax=ax)
        ax.set_title(col, fontsize=12, fontweight='bold')
        mean_v = df[col].mean()
        ax.axvline(mean_v, color='red', linestyle='--', alpha=0.7)
        ax.text(0.95, 0.95, f'μ={mean_v:.2f}\\nσ={df[col].std():.2f}',
                transform=ax.transAxes, ha='right', va='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        plot_idx += 1

    # Categorical counts
    for i, col in enumerate(categorical_cols[:n_categorical]):
        row, col_idx = divmod(plot_idx, ncols)
        ax = axes[row][col_idx]
        top_vals = df[col].value_counts().head(10)
        colors = PALETTE[:len(top_vals)] if isinstance(PALETTE, list) else None
        top_vals.plot(kind='barh', ax=ax, color=colors)
        ax.set_title(col, fontsize=12, fontweight='bold')
        ax.set_xlabel('Count')
        plot_idx += 1

    # Hide empty subplots
    for idx in range(plot_idx, nrows * ncols):
        row, col_idx = divmod(idx, ncols)
        axes[row][col_idx].set_visible(False)

    fig.suptitle("{{TITLE}}", fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
    print(f"EDA dashboard saved with {plot_idx} plots.")
'''

# ════════════════════════════════════════════════════════════════
# 10. POPULATION PYRAMID
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["population_pyramid"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
age_col = "{{X_AXIS}}"
gender_col = "{{HUE}}"

df = df.dropna(subset=[age_col, gender_col])

# Create age bins
bins = list(range(0, int(df[age_col].max()) + 10, 10))
labels = [f"{b}-{b+9}" for b in bins[:-1]]
df["age_group"] = pd.cut(df[age_col], bins=bins, labels=labels, right=False)

# Count by age group and gender
genders = df[gender_col].unique()[:2]
counts = df.groupby(["age_group", gender_col]).size().unstack(fill_value=0)

fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

y_pos = range(len(labels))

if len(genders) >= 2:
    color1 = PALETTE[0] if isinstance(PALETTE, list) else '#2196F3'
    color2 = PALETTE[1] if isinstance(PALETTE, list) else '#FF5722'

    vals1 = counts[genders[0]].values if genders[0] in counts.columns else np.zeros(len(labels))
    vals2 = counts[genders[1]].values if genders[1] in counts.columns else np.zeros(len(labels))

    ax.barh(y_pos, -vals1, color=color1, label=str(genders[0]), height=0.8)
    ax.barh(y_pos, vals2, color=color2, label=str(genders[1]), height=0.8)

    max_val = max(vals1.max(), vals2.max())
    ax.set_xlim(-max_val * 1.2, max_val * 1.2)
    ax.axvline(0, color='black', linewidth=0.5)

ax.set_yticks(y_pos)
ax.set_yticklabels(labels)
ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("{{XLABEL}}", fontsize=13)
ax.set_ylabel("{{YLABEL}}", fontsize=13)
ax.legend(fontsize=11)

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print("Population pyramid saved.")
'''

# ════════════════════════════════════════════════════════════════
# 11. ROC CURVE
# ════════════════════════════════════════════════════════════════
CHART_TEMPLATES["roc_curve"] = '''
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

plt.style.use('seaborn-v0_8-whitegrid')
PALETTE = {{PALETTE}}

df = pd.read_csv({{DATA_PATH}})
true_col = "{{X_AXIS}}"
pred_col = "{{Y_AXIS}}"

df = df.dropna(subset=[true_col, pred_col])

fpr, tpr, thresholds = roc_curve(df[true_col], df[pred_col])
roc_auc = auc(fpr, tpr)

fig, ax = plt.subplots(figsize=({{FIGSIZE_W}}, {{FIGSIZE_H}}), dpi={{DPI}})

color = PALETTE[0] if isinstance(PALETTE, list) else '#0072B2'
ax.plot(fpr, tpr, color=color, lw=2.5, label=f'ROC Curve (AUC = {roc_auc:.3f})')
ax.plot([0, 1], [0, 1], linestyle='--', color='gray', lw=1, label='Random Classifier')
ax.fill_between(fpr, tpr, alpha=0.1, color=color)

# Optimal threshold (Youden's J)
j_scores = tpr - fpr
optimal_idx = j_scores.argmax()
optimal_threshold = thresholds[optimal_idx]
ax.plot(fpr[optimal_idx], tpr[optimal_idx], 'ro', markersize=10,
        label=f'Optimal (threshold={optimal_threshold:.3f})')

ax.set_title("{{TITLE}}", fontsize=16, fontweight='bold', pad=20)
ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=13)
ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=13)
ax.legend(loc='lower right', fontsize=11)
ax.set_xlim(-0.01, 1.01)
ax.set_ylim(-0.01, 1.05)

plt.tight_layout()
plt.savefig({{OUTPUT_PATH}}, dpi={{DPI}}, bbox_inches='tight', facecolor='white')
print(f"ROC curve saved. AUC = {roc_auc:.3f}")
'''
