"""Figure 1: cheat vs tip note strength at the end of each day in Part 2 (2.1, 2.2, 2.3), one line per office."""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shortcut_paradox.logbook import read_events  # noqa: E402

TIP, CHEAT, INK, MUTED = "#2a78d6", "#eb6834", "#222222", "#888888"
panels = [("2.1", "No fading (2.1)"), ("2.2", "Medium fading (2.2)"), ("2.3", "Fast fading (2.3)")]
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK})
fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
for ax, (setup, title) in zip(axes, panels):
    for r in range(3):
        ev = [e for e in read_events(Path(f"results/part2/runs/{setup}_r{r}"))
              if e["event"] == "wiki_snapshot" and e["turn"] == 9]
        days = [e["day"] for e in ev]
        s = [{n["label"]: n["strength"] for n in e["notes"]} for e in ev]
        ax.plot(days, [x["cheat"] for x in s], color=CHEAT, lw=2, ls="--", marker="o", ms=4,
                label="Cheat note (Sam)" if r == 0 else None)
        ax.plot(days, [x["tip"] for x in s], color=TIP, lw=2, marker="s", ms=4,
                label="Tip note (Alex)" if r == 0 else None)
    ax.axvline(3.5, color=MUTED, lw=1, ls=":")
    ax.set_title(title, fontsize=10, color=INK)
    ax.set_xticks(range(1, 7)); ax.set_xlabel("Day")
    ax.grid(axis="y", color="#e6e6e6", lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
axes[0].set_ylabel("Note strength (end of day)")
h, l = axes[0].get_legend_handles_labels()
from matplotlib.lines import Line2D
h.append(Line2D([], [], color=MUTED, lw=1, ls=":")); l.append("Planted cheaters leave (after day 3)")
fig.legend(h, l, frameon=False, fontsize=9, loc="lower center", ncol=3)
fig.tight_layout(rect=(0, 0.08, 1, 1))
out = Path("paper/figure_1_strength.png")
fig.savefig(out, dpi=200)
print("saved", out)
