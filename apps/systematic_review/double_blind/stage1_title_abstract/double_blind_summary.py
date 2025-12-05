# -*- coding: utf-8 -*-
"""
double_blind_summary.py

Purpose:
    1. Read R1/R2 double-blind screening result files:
         data/systematic_review/double_blind/stage1_title_abstract/R1_analysis_results.xlsx
         data/systematic_review/double_blind/stage1_title_abstract/R2_analysis_results.xlsx
    2. Compute the distribution of values in the Decision column for each file.
    3. For records where Decision != "exclude", group by Decision and list the
       corresponding No. values.
    4. Write all summary statistics to a txt file in the same directory, with a
       clear, human-readable format for manual review and verification.
"""

import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd


class RoundDecisionAnalyzer:
    """
    Per-round (R1 or R2) double-blind screening decision analyzer.

    :param round_name: Round name (e.g., "R1" or "R2").
    :param result_path: Path to the result file (Excel) for this round.
    """

    def __init__(self, round_name: str, result_path: Path) -> None:
        """
        Initialize the per-round analyzer.

        :param round_name: Round name.
        :param result_path: Excel result file path for this round.
        """
        self.round_name = round_name
        self.result_path = result_path

    def _format_decision_counts(self, df: pd.DataFrame) -> str:
        """
        Format frequency statistics for each distinct value in the Decision column.

        :param df: Result DataFrame for the current round.
        :return: Formatted statistics as a text block.
        """
        if "Decision" not in df.columns:
            return "  [ERROR] 'Decision' column is missing; cannot compute statistics.\n"

        counts = df["Decision"].value_counts(dropna=False)
        if counts.empty:
            return "  [INFO] 'Decision' column is empty; nothing to summarize.\n"

        lines: List[str] = []
        for value, count in counts.items():
            label = "NaN" if pd.isna(value) else str(value)
            lines.append(f"  '{label}': {count} records")
        return "\n".join(lines) + "\n"

    def _format_non_exclude_by_decision(self, df: pd.DataFrame) -> str:
        """
        Group all records with Decision != 'exclude' and list their No. values.

        :param df: Result DataFrame for the current round.
        :return: Formatted text block.
        """
        required_cols = {"Decision", "No."}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            return (
                f"  [ERROR] Missing required columns: {missing_cols}; "
                "cannot list non-'exclude' records.\n"
            )

        # Normalize to strings and compare in lower case to avoid case mismatch.
        decision_str = df["Decision"].astype(str).str.strip()
        mask_non_exclude = decision_str.str.lower() != "exclude"
        filtered = df[mask_non_exclude].copy()

        total = len(filtered)
        lines: List[str] = []
        lines.append(f"  Total {total} records with Decision != 'exclude'.")

        if total == 0:
            lines.append("  No records requiring further attention.")
            return "\n".join(lines) + "\n"

        # Group by Decision and collect No. values.
        grouped = filtered.groupby(decision_str[mask_non_exclude].str.strip())

        for decision_value, group in grouped:
            # Try to convert No. to int for nicer display and sorting.
            no_series = group["No."]
            nos: List[str] = []
            for value in no_series:
                if pd.isna(value):
                    continue
                try:
                    nos.append(str(int(value)))
                except (ValueError, TypeError):
                    nos.append(str(value))
            nos_str = ", ".join(nos) if nos else ""
            label = "NaN" if decision_value.lower() == "nan" else decision_value
            lines.append(f"  {label}: [{nos_str}]")

        return "\n".join(lines) + "\n"

    def generate_report(self) -> str:
        """
        Read the current round results and generate the full summary section.

        :return: Formatted summary text for this round.
        """
        lines: List[str] = []

        # Round header block
        lines.append("------------------------------------------------------")
        lines.append(f"Round: {self.round_name}")
        lines.append(f"Result file: {self.result_path}")
        lines.append("")

        if not self.result_path.is_file():
            lines.append(f"[ERROR] File not found: {self.result_path}")
            lines.append("")
            return "\n".join(lines)

        try:
            df = pd.read_excel(self.result_path)
        except Exception as exc:
            lines.append(f"[ERROR] Failed to read Excel file: {exc}")
            lines.append("")
            return "\n".join(lines)

        # Decision distribution statistics
        lines.append("[1] Distribution of values in 'Decision' column")
        lines.append(self._format_decision_counts(df).rstrip())
        lines.append("")

        # Records with Decision != 'exclude'
        lines.append("[2] Records with Decision != 'exclude' (grouped by Decision)")
        lines.append(self._format_non_exclude_by_decision(df).rstrip())
        lines.append("")

        return "\n".join(lines)


class DoubleBlindSummaryGenerator:
    """
    Double-blind screening decision summary generator.

    :param base_dir: Base directory for double-blind results (containing R1/R2 files).
    :param output_txt_path: Output path for the summary txt file.
    """

    def __init__(self, base_dir: Path, output_txt_path: Path) -> None:
        """
        Initialize the summary generator.

        :param base_dir: Base directory for double-blind screening results.
        :param output_txt_path: Output txt file path for the summary.
        """
        self.base_dir = base_dir
        self.output_txt_path = output_txt_path

        # Round names and corresponding result file paths.
        self.round_result_files: Dict[str, Path] = {
            "R1": self.base_dir / "R1_analysis_results.xlsx",
            "R2": self.base_dir / "R2_analysis_results.xlsx",
        }

    def build_summary_text(self) -> str:
        """
        Build the complete double-blind screening decision summary text.

        :return: Summary text.
        """
        sections: List[str] = []

        # Global header
        header_lines: List[str] = [
            "======================================================",
            "Double-blind screening decision summary",
            f"Result directory: {self.base_dir}",
            f"Output file: {self.output_txt_path}",
            "======================================================",
            "",
        ]
        sections.append("\n".join(header_lines))

        # Per-round reports
        for round_name, file_path in self.round_result_files.items():
            analyzer = RoundDecisionAnalyzer(round_name, file_path)
            sections.append(analyzer.generate_report())

        # Separate sections with blank lines to improve readability.
        return "\n\n".join(sections).rstrip() + "\n"

    def write_summary(self, text: str) -> None:
        """
        Write the summary text to the target txt file.

        :param text: Summary text.
        :return: None
        """
        try:
            self.output_txt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_txt_path, "w", encoding="utf-8") as file:
                file.write(text)
            print(f"[INFO] Summary written to: {self.output_txt_path}")
        except Exception as exc:
            print(f"[ERROR] Failed to write summary txt file: {exc}")
            sys.exit(1)

    def run(self) -> None:
        """
        Execute the summary pipeline: build text, print to console, and write to file.

        :return: None
        """
        summary_text = self.build_summary_text()
        print(summary_text)
        self.write_summary(summary_text)


def main() -> None:
    """
    Script entry point: infer paths and run double-blind screening summary.

    :return: None
    """
    # Assume this script is located under apps/systematic_review/double_blind/
    project_root = Path(__file__).resolve().parents[3]
    base_dir = project_root / "data" / "systematic_review" / "double_blind" / "stage1_title_abstract"
    output_txt_path = base_dir / "double_blind_decision_summary.txt"

    summary_generator = DoubleBlindSummaryGenerator(base_dir, output_txt_path)
    summary_generator.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
