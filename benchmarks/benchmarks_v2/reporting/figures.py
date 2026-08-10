from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..orchestrator.data_models import AggregateReport


class FigureGenerator:
    """Generate benchmark visualization charts using matplotlib."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def generate_all(
        self,
        campaign_id: str,
        reports: List[AggregateReport],
        raw_results: Optional[List[Any]] = None,
    ) -> List[Path]:
        """Generate all standard charts and return their paths."""
        paths: List[Path] = []

        fig_dir = self._output_dir / campaign_id / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)

        paths.append(self.bar_chart_f1(fig_dir, reports))
        paths.append(self.boxplot_latency(fig_dir, reports))
        paths.append(self.bar_chart_pass_rate(fig_dir, reports))
        paths.append(self.precision_recall_scatter(fig_dir, reports))

        if raw_results:
            paths.append(self.line_chart_by_seed(fig_dir, raw_results))

        return [p for p in paths if p is not None]

    def bar_chart_f1(
        self, fig_dir: Path, reports: List[AggregateReport]
    ) -> Path:
        """Bar chart of mean F1 per family."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return fig_dir / "f1_bar.png"

        families = [r.family for r in reports]
        f1s = [r.f1 for r in reports]

        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(families, f1s, color="#6366f1", edgecolor="#818cf8", linewidth=0.5)
        ax.set_xlabel("Family", fontsize=11)
        ax.set_ylabel("Mean F1 Score", fontsize=11)
        ax.set_title("F1 Score by Benchmark Family", fontsize=14, fontweight="bold")
        ax.set_ylim(0, 1.05)
        ax.tick_params(axis="x", rotation=45)

        for bar, val in zip(bars, f1s):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=8)

        plt.tight_layout()
        path = fig_dir / "f1_bar.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def boxplot_latency(
        self, fig_dir: Path, reports: List[AggregateReport]
    ) -> Path:
        """Bar chart of median and P95 latency per family."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return fig_dir / "latency_boxplot.png"

        families = [r.family for r in reports]
        medians = [r.median_latency for r in reports]
        p95s = [r.p95_latency for r in reports]

        fig, ax = plt.subplots(figsize=(12, 6))
        x_pos = range(len(families))

        ax.bar(x_pos, medians, color="#3b82f6", alpha=0.7, label="Median", width=0.4)
        ax.bar([x + 0.4 for x in x_pos], p95s, color="#ef4444", alpha=0.7, label="P95", width=0.4)

        ax.set_xlabel("Family", fontsize=11)
        ax.set_ylabel("Latency (ms)", fontsize=11)
        ax.set_title("Latency Distribution by Family", fontsize=14, fontweight="bold")
        ax.set_xticks([x + 0.2 for x in x_pos])
        ax.set_xticklabels(families, rotation=45, ha="right")
        ax.legend()

        plt.tight_layout()
        path = fig_dir / "latency_boxplot.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def bar_chart_pass_rate(
        self, fig_dir: Path, reports: List[AggregateReport]
    ) -> Path:
        """Bar chart of pass rate per family."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return fig_dir / "pass_rate_bar.png"

        families = [r.family for r in reports]
        rates = [r.pass_rate for r in reports]

        fig, ax = plt.subplots(figsize=(12, 6))
        colors = ["#22c55e" if r >= 0.9 else "#f59e0b" if r >= 0.7 else "#ef4444" for r in rates]
        bars = ax.bar(families, rates, color=colors, edgecolor="#374151", linewidth=0.5)
        ax.set_xlabel("Family", fontsize=11)
        ax.set_ylabel("Pass Rate", fontsize=11)
        ax.set_title("Pass Rate by Benchmark Family", fontsize=14, fontweight="bold")
        ax.set_ylim(0, 1.1)
        ax.tick_params(axis="x", rotation=45)
        ax.axhline(y=0.9, color="#22c55e", linestyle="--", alpha=0.5, label="90% target")
        ax.legend()

        for bar, val in zip(bars, rates):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{val:.1%}", ha="center", va="bottom", fontsize=8)

        plt.tight_layout()
        path = fig_dir / "pass_rate_bar.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def precision_recall_scatter(
        self, fig_dir: Path, reports: List[AggregateReport]
    ) -> Path:
        """Scatter plot of precision vs recall per family."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return fig_dir / "precision_recall_scatter.png"

        fig, ax = plt.subplots(figsize=(8, 8))

        for r in reports:
            ax.scatter(
                r.precision,
                r.recall,
                s=100,
                alpha=0.8,
                label=r.family,
            )
            ax.annotate(
                r.family,
                (r.precision, r.recall),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
            )

        ax.set_xlabel("Mean Precision", fontsize=11)
        ax.set_ylabel("Mean Recall", fontsize=11)
        ax.set_title("Precision vs Recall", fontsize=14, fontweight="bold")
        ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.3, label="y=x")

        plt.tight_layout()
        path = fig_dir / "precision_recall_scatter.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def line_chart_by_seed(
        self, fig_dir: Path, results: List[Any]
    ) -> Path:
        """Line chart of F1 scores grouped by seed."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return fig_dir / "f1_by_seed.png"

        seed_groups: Dict[int, Dict[str, List[float]]] = {}
        for r in results:
            seed = getattr(r, "seed", 0)
            family = getattr(r, "family", "unknown")
            f1 = getattr(r, "f1", 0.0)
            seed_groups.setdefault(seed, {}).setdefault(family, []).append(f1)

        fig, ax = plt.subplots(figsize=(12, 6))

        for seed, families in sorted(seed_groups.items()):
            family_names = sorted(families.keys())
            mean_f1s = [sum(families[f]) / len(families[f]) for f in family_names]
            ax.plot(family_names, mean_f1s, marker="o", label=f"Seed {seed}", alpha=0.8)

        ax.set_xlabel("Family", fontsize=11)
        ax.set_ylabel("Mean F1", fontsize=11)
        ax.set_title("F1 Score by Seed Across Families", fontsize=14, fontweight="bold")
        ax.tick_params(axis="x", rotation=45)
        ax.legend()

        plt.tight_layout()
        path = fig_dir / "f1_by_seed.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path
