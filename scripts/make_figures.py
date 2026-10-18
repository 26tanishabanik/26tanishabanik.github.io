"""Figures for the post. Values are the measured results recorded in notes/findings_so_far.md
(sealed held-out set, 29 tasks; hidden-state analysis of 2026-10-16)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"   # validated categorical slots 1-3 (light)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})
OUT = "../assets/img"


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


# 1. results: three measures, original vs the trained model's two test runs (out of 29 tasks each)
measures = ["Already fixed:\nchanged the code anyway", "Already fixed:\nsubmitted with no change", "Bug present:\nfixed"]
series = [("Original model", [24, 0, 15], S1), ("Trained, test run 1", [8, 18, 18], S2), ("Trained, test run 2", [4, 23, 18], S3)]
fig, ax = plt.subplots(figsize=(8.2, 4.4))
w = 0.26
for i, (name, vals, c) in enumerate(series):
    xs = [m + (i - 1) * w for m in range(len(measures))]
    bars = ax.bar(xs, vals, width=w - 0.03, color=c, label=name, edgecolor=SURFACE, linewidth=2)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.5, str(v), ha="center", va="bottom", fontsize=10, color=INK)
ax.set_xticks(range(len(measures)), measures)
ax.set_ylim(0, 29)
ax.set_ylabel("tasks (of 29)")
ax.set_title("Training on clean examples: fewer unneeded edits, no lost bug fixes", loc="left", fontsize=12, color=INK)
style(ax)
ax.legend(frameon=False, loc="upper right", fontsize=10)
fig.tight_layout()
fig.savefig(f"{OUT}/results.png", dpi=200)

# 2. where and when the keep-or-change judgement is readable (linear probe AUC on held-out runs)
layers = [3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51, 55, 59, 63]
auc_layer = [0.804, 0.832, 0.852, 0.858, 0.860, 0.858, 0.882, 0.884, 0.887, 0.882, 0.884, 0.881, 0.864, 0.855, 0.848, 0.840]
steps = ["0", "1-2", "3-5", "6-10", "11-20", "21+"]
auc_step = [0.501, 0.626, 0.858, 0.948, 0.935, 0.858]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.8), sharey=True)
a1.plot(layers, auc_layer, color=S1, linewidth=2, marker="o", markersize=5)
a1.annotate("best: layer 35, 0.887", (35, 0.887), xytext=(30, 0.95), fontsize=10, color=INK2)
a1.set_xlabel("layer (of 64)")
a1.set_ylabel("AUC (0.5 = chance)")
a1.set_title("By layer", loc="left", fontsize=12)
a2.plot(range(len(steps)), auc_step, color=S1, linewidth=2, marker="o", markersize=5)
a2.set_xticks(range(len(steps)), steps)
a2.set_xlabel("agent step")
a2.set_title("By step (layer 35)", loc="left", fontsize=12)
for a in (a1, a2):
    a.axhline(0.5, color=INK2, linewidth=0.8, linestyle=(0, (4, 3)))
    a.set_ylim(0.45, 1.0)
    style(a)
a2.text(4.2, 0.515, "chance", fontsize=9, color=INK2)
fig.tight_layout()
fig.savefig(f"{OUT}/probe.png", dpi=200)

# 3. the setup: one bug report, two versions of the repository, one sealed environment
fig, ax = plt.subplots(figsize=(10.4, 3.9))
ax.set_xlim(0, 11.4); ax.set_ylim(0, 4.1); ax.axis("off")
def box(x, y, w, h, title, body, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", linewidth=1.6,
                                edgecolor=edge, facecolor=SURFACE))
    ax.text(x + 0.18, y + h - 0.25, title, fontsize=11, fontweight="bold", color=INK, va="top")
    ax.text(x + 0.18, y + h - 0.68, body, fontsize=9.6, color=INK2, va="top", linespacing=1.45)
box(0.1, 1.15, 2.7, 1.75, "Bug report", "a real GitHub issue,\ncreated after the\nmodel's release", INK2)
box(3.5, 2.2, 3.7, 1.75, "Version A: bug present", "repository just before the fix\ncorrect = hidden tests pass", INK2)
box(3.5, 0.15, 3.7, 1.75, "Version B: already fixed", "official fix applied\ncorrect = submit NO change\nand the tests still pass", INK2)
box(7.9, 0.55, 3.4, 2.95, "Sealed container", "same single commit\nsame timestamps\nno network\nno stale installed copies\nfresh process state", INK)
for y in (3.07, 1.03):
    ax.annotate("", (3.48, y), (2.82, 2.02), arrowprops=dict(arrowstyle="-|>", color=INK2, linewidth=1.2))
    ax.annotate("", (7.88, 2.02), (7.22, y), arrowprops=dict(arrowstyle="-|>", color=INK2, linewidth=1.2))
fig.savefig(f"{OUT}/setup.png", dpi=200, bbox_inches="tight")
print("figures written")
