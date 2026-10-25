"""Figures for the post "Most Turns Are Easy". Values are the measured results in ~/Projects/indic-decision
(results/v6b_r150_full, results/compare_llm, results/speed, results/usecases, results/gate_v6b_v7.txt)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2, S3, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#bdbab3"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})
OUT = "../assets/img"


def style(ax, grid="x"):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def hbars(ax, labels, vals, colors, fmt, xmax):
    ys = range(len(labels))[::-1]
    ax.barh(list(ys), vals, color=colors, height=0.62)
    for y, v in zip(ys, vals):
        ax.text(v + xmax * 0.01, y, fmt(v), va="center", fontsize=10.5, color=INK)
    ax.set_yticks(list(ys), labels)
    ax.set_xlim(0, xmax)


# 1. translated everyday decision tasks (JevBench), 1,295 native-script items in 11 Indian languages
fig, ax = plt.subplots(figsize=(8.2, 3.3))
hbars(ax, ["Jev (hosted)", "This model (open)", "Yama (open)", "Laya, multilingual (open)", "Vega (open)"],
      [98.1, 85.5, 80.3, 50.3, 45.2], [S1, S2, GREY, GREY, GREY], lambda v: f"{v:.1f}%", 108)
ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
ax.set_title("Everyday decision tasks in Indian languages: accuracy", loc="left", fontsize=12, color=INK)
style(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/decision-usecases.png", dpi=200)

# 2. where the decision model sits in a voice agent
fig, ax = plt.subplots(figsize=(8.6, 3.2))
ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")


def box(x, y, w, h, title, sub, edge, face):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6", linewidth=1.4,
                                edgecolor=edge, facecolor=face))
    ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", fontsize=11, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", fontsize=9.5, color=INK2)


def arrow(x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color="#8d877d", lw=1.4))


box(1, 15, 17, 10, "Caller speaks", "speech-to-text", S1, "#eaf2fc")
box(24, 13, 22, 14, "Decision model", "answer + confidence\nper question", S2, "#fdeee6")
box(54, 26, 19, 9, "Sure enough", "use its answer", S3, "#e5f6ef")
box(54, 5, 19, 9, "Not sure", "ask the LLM", "#d9822b", "#fbefe2")
box(80, 15, 18, 10, "Bot replies", "LLM + voice", S1, "#eaf2fc")
arrow(18.6, 20, 23.4, 20); arrow(46.6, 23, 53.4, 30); arrow(46.6, 17, 53.4, 10)
arrow(73.6, 30, 79.4, 23); arrow(73.6, 10, 79.4, 17)
ax.text(50, 0.5, 'The bar for "sure enough" is set separately for each kind of question', ha="center", fontsize=9.5, color=INK2)
fig.tight_layout()
fig.savefig(f"{OUT}/decision-pipeline.png", dpi=200)

# 3. caller replies read correctly, by language (6,502 test replies)
langs = ["Hindi", "Marathi", "Odia", "Telugu", "English", "Bengali", "Gujarati", "Malayalam", "Punjabi", "Tamil", "Kannada",
         "Assamese (never in training)"]
acc = [98.8, 98.2, 97.6, 97.6, 97.2, 97.1, 96.9, 96.6, 96.4, 96.0, 95.2, 89.2]
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ys = range(len(langs))[::-1]
ax.barh(list(ys), [a - 80 for a in acc], left=80, height=0.62, color=[GREY if l == "English" else S2 if l.startswith("Assamese") else S1 for l in langs])
for y, a in zip(ys, acc):
    ax.text(a + 0.25, y, f"{a:.1f}", va="center", fontsize=10, color=INK)
ax.set_yticks(list(ys), langs)
ax.set_xlim(80, 101.5)
ax.set_xticks([80, 85, 90, 95, 100], ["80%", "85%", "90%", "95%", "100%"])
ax.set_title("Caller replies read correctly, by language", loc="left", fontsize=12, color=INK)
style(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/decision-languages.png", dpi=200)

# 4. share of replies decided alone vs accuracy on them (6,502 test replies, sorted by confidence)
cov = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
prec = [1.0, 1.0, 1.0, 1.0, .9988, .9985, .9987, .9988, .9986, .9988, .9986, .9982, .9983, .998, .9969, .9963, .9946, .9909, .983, .9637]
fig, ax = plt.subplots(figsize=(8.2, 3.9))
ax.plot([c * 100 for c in cov], [p * 100 for p in prec], color=S1, linewidth=2.4)
ax.axhline(99, color="#c0392b", linestyle="--", linewidth=1.2)
ax.text(3, 99.08, "99% target", color="#c0392b", fontsize=10)
ax.scatter([83.8], [99.52], s=60, color=S2, zorder=5)
ax.annotate("cutoff 0.987: 84% of replies\ndecided alone, 99.5% right", (83.8, 99.52), xytext=(46, 97.6), fontsize=10, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.annotate("answers everything: 96.3%", (100, 96.37), xytext=(70, 96.5), fontsize=10, color=INK2)
ax.set_xlim(0, 101); ax.set_ylim(96, 100.25)
ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
ax.set_yticks([97, 98, 99, 100], ["97%", "98%", "99%", "100%"])
ax.set_xlabel("share of replies the model decides on its own")
ax.set_title("The more turns the model takes on alone, the lower its accuracy on them", loc="left", fontsize=12, color=INK)
style(ax, grid="y")
fig.tight_layout()
fig.savefig(f"{OUT}/decision-coverage.png", dpi=200)

# 5. next to Sarvam's LLM (2,700 test turns): share of turns sent to the LLM, accuracy on the right
rows = ["LLM on every turn", "This model where a cutoff is proven,\nLLM elsewhere", "Hand-off rules chosen on\nseparate calibration calls",
        "Hand-off rules tuned on calls\nlike the test calls"]
share, accs = [100, 59.5, 25.3, 22], ["92.8%", "93.4%", "94.3%", "~95%"]
fig, ax = plt.subplots(figsize=(8.2, 3.6))
ys = range(len(rows))[::-1]
ax.barh(list(ys), share, height=0.58, color=[GREY, "#f0a072", S2, S2])
for y, s_, a in zip(ys, share, accs):
    ax.text(s_ + 1.5, y, f"{s_:.0f}%" if s_ != 22 else "~22%", va="center", fontsize=10, color=INK2)
    ax.text(128, y, a, va="center", ha="right", fontsize=12, fontweight="bold", color=INK)
ax.set_yticks(list(ys), rows)
ax.set_xlim(0, 129)
ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("share of turns sent to the LLM")
ax.set_title("Turns sent to the LLM (bars) and accuracy (right)", loc="left", fontsize=12, color=INK)
style(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/decision-llm.png", dpi=200)

# 6. time for one pass of the model (median), against one LLM call
fig, ax = plt.subplots(figsize=(8.2, 3.3))
hbars(ax, ["This model, H100 GPU", "This model, A10G GPU", "This model, L4 GPU", "This model, T4 GPU", "This model, laptop (Apple M5)",
           "LLM, one API call"], [15, 23, 32, 71, 103, 380], [S2, S2, S2, S2, "#f0a072", GREY], lambda v: f"{v:.0f} ms", 430)
ax.set_xlabel("milliseconds")
ax.set_title("Time for one pass of the model", loc="left", fontsize=12, color=INK)
style(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/decision-latency.png", dpi=200)

# 7. same data, different teachers: confident mistakes on 1,011 unseen business-rule questions
fig, ax = plt.subplots(figsize=(8.2, 2.5))
ys = [1, 0]
ax.barh(ys, [70, 3], height=0.55, color=["#d9822b", S3])
ax.text(71.5, 1, "70", va="center", fontsize=11, fontweight="bold")
ax.text(4.5, 0, "3", va="center", fontsize=11, fontweight="bold")
for y, a in zip(ys, ["81.6%", "82.4%"]):
    ax.text(99, y, f"accuracy {a}", va="center", ha="right", fontsize=10.5, color=INK2)
ax.set_yticks(ys, ["More confident teachers", "Calmer teachers"])
ax.set_xlim(0, 100)
ax.set_xlabel("confident mistakes (out of 1,011)")
ax.set_title("Same data, different teachers", loc="left", fontsize=12, color=INK)
style(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/decision-teachers.png", dpi=200)

# 8. current model vs next version on the patterns found in live calls (held-out tests)
pats = ["Kind of non-answer", "Routing to the right service", '"Yes, but…" replies', "Answered every part?", "Details offered unasked"]
cur, nxt = [50.5, 78.7, 94.3, 84.5, 93.3], [97.3, 92.5, 97.1, 89.4, 95.5]
fig, ax = plt.subplots(figsize=(8.2, 4.3))
ys = [i * 1.0 for i in range(len(pats))][::-1]
h = 0.36
ax.barh([y + h / 2 for y in ys], cur, height=h, color=GREY, label="current model")
ax.barh([y - h / 2 for y in ys], nxt, height=h, color=S2, label="next version")
for y, c, n in zip(ys, cur, nxt):
    ax.text(c + 0.8, y + h / 2, f"{c:.1f}", va="center", fontsize=9.5, color=INK2)
    ax.text(n + 0.8, y - h / 2, f"{n:.1f}", va="center", fontsize=9.5, fontweight="bold", color=INK)
ax.set_yticks(ys, pats)
ax.set_xlim(0, 108)
ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.07), ncol=2, fontsize=10)
ax.set_title("Patterns found in live calls: current model and next version", loc="left", fontsize=12, color=INK)
style(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/decision-nextround.png", dpi=200)
print("done")
