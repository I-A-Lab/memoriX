from __future__ import annotations

import statistics
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..orchestrator.data_models import AggregateReport


class ReportGenerator:
    """Generate benchmark reports in multiple formats (MD, JSON)."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def generate(
        self,
        campaign_id: str,
        profile: str,
        families: List[str],
        aggregate_reports: List[AggregateReport],
        raw_results: Optional[List[Any]] = None,
    ) -> Path:
        """Generate the full Markdown report and return its path."""
        campaign_dir = self._output_dir / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)

        md_path = campaign_dir / "report.md"
        md_content = self._render_markdown(campaign_id, profile, families, aggregate_reports, raw_results)

        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(md_content)

        return md_path

    def _render_markdown(
        self,
        campaign_id: str,
        profile: str,
        families: List[str],
        reports: List[AggregateReport],
        raw_results: Optional[List[Any]] = None,
    ) -> str:
        """Render the complete Markdown report."""
        sections: List[str] = []

        # Section 1: Title
        sections.append(f"# memoriX Benchmark Report\n")
        sections.append(f"**Campaign ID:** `{campaign_id}`\n")
        sections.append(f"**Profile:** {profile}\n")
        sections.append(f"**Families:** {', '.join(families)}\n")
        sections.append("")

        # Section 2: Executive Summary
        sections.append("## 1. Executive Summary\n")
        total_runs = sum(r.total_runs for r in reports)
        total_failed = sum(r.failed_runs for r in reports)
        overall_pass_rate = (total_runs - total_failed) / max(total_runs, 1)
        sections.append(f"- Total runs: {total_runs}")
        sections.append(f"- Passed: {total_runs - total_failed}")
        sections.append(f"- Failed: {total_failed}")
        sections.append(f"- Overall pass rate: {overall_pass_rate:.1%}")
        sections.append("")

        # Section 3: Per-Family Metrics
        sections.append("## 2. Per-Family Metrics\n")
        sections.append("| Family | Suite | Precision | Recall | F1 | Pass Rate | Median Lat. | P95 Lat. |")
        sections.append("|--------|-------|-----------|--------|----|-----------|------------:|---------:|")
        for r in reports:
            sections.append(
                f"| {r.family} | {r.suite} | {r.precision:.4f} | {r.recall:.4f} | "
                f"{r.f1:.4f} | {r.pass_rate:.1%} | {r.median_latency:.1f}ms | "
                f"{r.p95_latency:.1f}ms |"
            )
        sections.append("")

        # Section 4: Detailed per-family sections
        for idx, r in enumerate(reports, start=3):
            sections.append(f"## {idx}. {r.family} - Detailed Results\n")
            sections.append(f"### Metrics")
            sections.append(f"- Suite: {r.suite}")
            sections.append(f"- Precision: {r.precision:.4f}")
            sections.append(f"- Recall: {r.recall:.4f}")
            sections.append(f"- F1: {r.f1:.4f}")
            sections.append(f"- Median Latency: {r.median_latency:.1f}ms")
            sections.append(f"- P95 Latency: {r.p95_latency:.1f}ms")
            sections.append(f"- Pass Rate: {r.pass_rate:.1%}")
            sections.append(f"- Total Runs: {r.total_runs}")
            sections.append(f"- Failed Runs: {r.failed_runs}")
            sections.append("")

            if r.statistical_tests:
                sections.append("### Statistical Tests\n")
                sections.append("| Test | Metric | Statistic | P-Value | Significant | Effect Size |")
                sections.append("|------|--------|----------:|--------:|-------------|------------:|")
                for t in r.statistical_tests:
                    sig = "Yes" if t.significant else "No"
                    sections.append(
                        f"| {t.test_name} | {t.metric} | {t.statistic:.4f} | "
                        f"{t.p_value:.4f} | {sig} | {t.effect_size:.4f} |"
                    )
                sections.append("")

        # Failure breakdown
        sections.append(f"## {len(reports) + 3}. Failure Breakdown\n")
        if raw_results:
            failure_counts: Dict[str, int] = {}
            for r in raw_results:
                fc = getattr(r, "failure_category", "PASS")
                if fc != "PASS":
                    failure_counts[fc] = failure_counts.get(fc, 0) + 1

            if failure_counts:
                sections.append("| Category | Count |")
                sections.append("|----------|------:|")
                for cat, count in sorted(failure_counts.items(), key=lambda x: -x[1]):
                    sections.append(f"| {cat} | {count} |")
            else:
                sections.append("No failures recorded.")
        else:
            sections.append("Raw results not available for failure breakdown.")
        sections.append("")

        # Configuration appendix
        sections.append(f"## {len(reports) + 4}. Configuration\n")
        sections.append(f"- Profile: {profile}")
        sections.append(f"- Families: {', '.join(families)}")
        sections.append(f"- Campaign: {campaign_id}")
        sections.append("")

        return "\n".join(sections)

    def generate_docx(
        self,
        campaign_id: str,
        profile: str,
        families: List[str],
        aggregate_reports: List[AggregateReport],
    ) -> Path:
        """Generate a DOCX report."""
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            raise RuntimeError("python-docx is required for DOCX generation")

        campaign_dir = self._output_dir / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)
        docx_path = campaign_dir / "report.docx"

        doc = Document()

        # Title
        title = doc.add_heading("memoriX Benchmark Report", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(f"Campaign ID: {campaign_id}")
        doc.add_paragraph(f"Profile: {profile}")
        doc.add_paragraph(f"Families: {', '.join(families)}")

        # Summary
        doc.add_heading("Executive Summary", level=1)
        total_runs = sum(r.total_runs for r in aggregate_reports)
        total_failed = sum(r.failed_runs for r in aggregate_reports)
        doc.add_paragraph(f"Total runs: {total_runs}")
        doc.add_paragraph(f"Passed: {total_runs - total_failed}")
        doc.add_paragraph(f"Failed: {total_failed}")
        doc.add_paragraph(f"Pass rate: {(total_runs - total_failed) / max(total_runs, 1):.1%}")

        # Per-family table
        doc.add_heading("Per-Family Metrics", level=1)
        table = doc.add_table(rows=1, cols=7)
        table.style = "Light Grid Accent 1"
        headers = ["Family", "Precision", "Recall", "F1", "Pass Rate", "Median Lat.", "P95 Lat."]
        for i, header in enumerate(headers):
            table.rows[0].cells[i].text = header

        for r in aggregate_reports:
            row = table.add_row()
            row.cells[0].text = r.family
            row.cells[1].text = f"{r.precision:.4f}"
            row.cells[2].text = f"{r.recall:.4f}"
            row.cells[3].text = f"{r.f1:.4f}"
            row.cells[4].text = f"{r.pass_rate:.1%}"
            row.cells[5].text = f"{r.median_latency:.1f}ms"
            row.cells[6].text = f"{r.p95_latency:.1f}ms"

        doc.save(str(docx_path))
        return docx_path

    def generate_pdf(
        self,
        campaign_id: str,
        profile: str,
        families: List[str],
        aggregate_reports: List[AggregateReport],
    ) -> Path:
        """Generate a PDF report.

        Attempts conversion in order:
        1. markdown + weasyprint (HTML-to-PDF)
        2. pandoc via subprocess (Markdown-to-PDF)
        3. Raises RuntimeError if neither tool is available.
        """
        campaign_dir = self._output_dir / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = campaign_dir / "report.pdf"

        # Ensure the Markdown source exists so pandoc can reference it too.
        md_path = campaign_dir / "report.md"
        if not md_path.exists():
            self.generate(campaign_id, profile, families, aggregate_reports)

        # --- Strategy 1: markdown + weasyprint ---
        try:
            import markdown as md_lib  # type: ignore[import-untyped]
            from weasyprint import HTML  # type: ignore[import-untyped]

            md_text = md_path.read_text(encoding="utf-8")
            html_body = md_lib.markdown(
                md_text,
                extensions=["tables", "fenced_code"],
            )
            full_html = (
                "<!DOCTYPE html>\n<html>\n<head>\n"
                '<meta charset="utf-8">\n'
                "<style>\n"
                "body { font-family: sans-serif; margin: 2em; line-height: 1.5; }\n"
                "table { border-collapse: collapse; width: 100%; margin: 1em 0; }\n"
                "th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }\n"
                "th { background: #f5f5f5; }\n"
                "h1, h2, h3 { margin-top: 1.2em; }\n"
                "code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }\n"
                "</style>\n</head>\n<body>\n"
                f"{html_body}\n"
                "</body>\n</html>"
            )
            HTML(string=full_html).write_pdf(str(pdf_path))
            return pdf_path

        except Exception:
            pass  # Fall through to pandoc.

        # --- Strategy 2: pandoc via subprocess ---
        try:
            result = subprocess.run(
                [
                    "pandoc",
                    str(md_path),
                    "-o",
                    str(pdf_path),
                    "--pdf-engine=xelatex",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and pdf_path.exists():
                return pdf_path
        except FileNotFoundError:
            pass  # pandoc not installed.

        # --- Strategy 3: graceful error ---
        raise RuntimeError(
            "PDF generation requires either weasyprint or pandoc to be installed."
        )

    def generate_all(
        self,
        campaign_id: str,
        profile: str,
        families: List[str],
        aggregate_reports: List[AggregateReport],
    ) -> Dict[str, Optional[Path]]:
        """Generate Markdown, DOCX, and PDF reports in sequence.

        Returns a dict mapping format name to its output Path.
        Individual format failures are caught and recorded as ``None``
        so that a PDF error does not prevent the other formats.
        """
        results: Dict[str, Optional[Path]] = {"md": None, "docx": None, "pdf": None}

        # 1. Markdown
        try:
            results["md"] = self.generate(
                campaign_id, profile, families, aggregate_reports
            )
        except Exception:
            pass

        # 2. DOCX
        try:
            results["docx"] = self.generate_docx(
                campaign_id, profile, families, aggregate_reports
            )
        except Exception:
            pass

        # 3. PDF
        try:
            results["pdf"] = self.generate_pdf(
                campaign_id, profile, families, aggregate_reports
            )
        except Exception:
            pass

        return results

    def generate_figures_from_raw(
        self,
        raw_results_path: Path,
        aggregate_reports: List[AggregateReport],
    ) -> Dict[str, Path]:
        """Regenerate all PNG charts from raw results.

        Uses :class:`FigureGenerator` to produce the standard set of
        visualization figures.  Returns a mapping of figure name to its
        output path.

        Parameters
        ----------
        raw_results_path:
            Path to a JSON file containing the raw per-run results.
        aggregate_reports:
            Pre-computed aggregate reports used by every chart.
        """
        from .figures import FigureGenerator

        fig_gen = FigureGenerator(self._output_dir)

        # Load raw results from disk.
        import json

        raw_results: Optional[List[Any]] = None
        if raw_results_path.exists():
            with open(raw_results_path, "r", encoding="utf-8") as fh:
                raw_results = json.load(fh)

        # Determine a campaign_id from the path (parent directory name).
        campaign_id = raw_results_path.parent.name

        paths = fig_gen.generate_all(campaign_id, aggregate_reports, raw_results)

        # Map the well-known filenames to their full paths.
        fig_dir = self._output_dir / campaign_id / "figures"
        known_names = [
            "f1_bar",
            "latency_boxplot",
            "pass_rate_bar",
            "precision_recall_scatter",
            "f1_by_seed",
        ]
        result: Dict[str, Path] = {}
        for name in known_names:
            candidate = fig_dir / f"{name}.png"
            if candidate.exists():
                result[name] = candidate

        return result
