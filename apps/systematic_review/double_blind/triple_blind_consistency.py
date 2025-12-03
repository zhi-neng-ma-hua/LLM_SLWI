# -*- coding: utf-8 -*-
"""
triple_blind_consistency.py

Purpose:
    Based on the three-round screening result file:
        data/systematic_review/double_blind/stage1_title_abstract/R1_R2_R3_analysis_results.xlsx

    Perform the following statistics and summaries:

    1. Under the condition Need_R3 = "yes", summarize the distribution of values
       in the R3_Decision column.

    2. Under the condition Need_R3 = "yes", count how many rows in R3_Notes are:
         - "Access restrictions."
         - "Payment restrictions."
         - "Non-English literature"

    3. Count the number of finally included studies (Final Included):
         (1) R1_Decision = R2_Decision = 'include'
         (2) R1_Decision = R2_Decision = 'unsure' and R3_Decision = 'include'
         (3) R1_Decision ≠ R2_Decision and R3_Decision = 'include'
       For each category, output the corresponding No. list for manual inspection.

    4. Count the number of finally excluded studies (Final Excluded):
         (1) R1_Decision = R2_Decision = 'exclude'
         (2) R1_Decision = R2_Decision = 'unsure' and R3_Decision = 'exclude'
         (3) R1_Decision ≠ R2_Decision and R3_Decision = 'exclude'

    5. Print all results to the terminal and write them to a txt file in the same
       directory for easy review and archiving.

Author: SmartMahua <zhinengmahua@gmail.com>
Date: 2025-05-22
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


class TripleBlindConsistencyAnalyzer:
    """
    Consistency analyzer for three-round (R1/R2/R3) screening results.

    :param base_dir: Root directory containing R1_R2_R3_analysis_results.xlsx.
    :param output_txt_path: Output path for the summary report (txt).
    """

    def __init__(self, base_dir: Path, output_txt_path: Path) -> None:
        """
        Initialize the analyzer.

        :param base_dir: Root directory containing result files.
        :param output_txt_path: Output path for the summary report (txt).
        :return: None
        """
        self.base_dir = base_dir
        self.output_txt_path = output_txt_path
        self.input_path = self.base_dir / "R1_R2_R3_analysis_results.xlsx"

    def load_results(self) -> pd.DataFrame:
        """
        Load and normalize the three-round screening results.

        :return: Normalized DataFrame.
        """
        if not self.input_path.is_file():
            raise FileNotFoundError(f"Result file not found: {self.input_path}")

        df = pd.read_excel(self.input_path)

        required_cols = {
            "No.",
            "Title",
            "Year",
            "R1_Decision",
            "R2_Decision",
            "R3_Decision",
            "R3_Notes",
            "Need_R3",
        }
        missing = required_cols - set(df.columns)
        if missing:
            raise KeyError(f"Result file is missing required columns: {missing}")

        # Normalize Decision / Need_R3 text: strip whitespace and convert to lower case
        for col in ["R1_Decision", "R2_Decision", "R3_Decision", "Need_R3"]:
            df[col] = df[col].astype(str).str.strip().str.lower()

        # Normalize Year as string
        df["Year"] = df["Year"].astype(str).str.strip()

        # Keep Notes as raw text, only fill missing values
        df["R3_Notes"] = df["R3_Notes"].fillna("").astype(str)

        return df

    @staticmethod
    def _extract_no_list(series: pd.Series) -> List[str]:
        """
        Extract No. values as a list of strings.

        :param series: Series corresponding to the "No." column.
        :return: List of No. values as strings.
        """
        nos: List[str] = []
        for v in series:
            if pd.isna(v):
                continue
            try:
                nos.append(str(int(v)))
            except (ValueError, TypeError):
                nos.append(str(v).strip())
        return nos

    def summarize_r3_decision_distribution(self, df: pd.DataFrame) -> Tuple[str, Dict[str, int]]:
        """
        Summarize R3_Decision distribution under the condition Need_R3 = 'yes'.

        :param df: Full result DataFrame.
        :return: (Formatted text, counts dictionary).
        """
        mask_need_r3 = df["Need_R3"] == "yes"
        subset = df[mask_need_r3]

        counts = subset["R3_Decision"].value_counts(dropna=False)
        summary = {("NaN" if pd.isna(k) else str(k)): int(v) for k, v in counts.items()}

        lines: List[str] = []
        lines.append("[R3_Decision distribution where Need_R3 = 'yes']")
        lines.append(f"  Total records with Need_R3 = 'yes': {len(subset)}")

        if subset.empty:
            lines.append("  No records require R3 decisions.")
            return "\n".join(lines) + "\n", summary

        for value, count in counts.items():
            label = "NaN" if pd.isna(value) else str(value)
            lines.append(f"  '{label}': {count} records")

        return "\n".join(lines) + "\n", summary

    def summarize_r3_restriction_notes(self, df: pd.DataFrame) -> str:
        """
        Count specific R3_Notes values under the condition Need_R3 = 'yes'.

        Tracked notes:
          - "Access restrictions."
          - "Payment restrictions."
          - "Non-English literature"

        :param df: Full result DataFrame.
        :return: Formatted text.
        """
        mask_need_r3 = df["Need_R3"] == "yes"
        subset = df[mask_need_r3]

        access_count = int((subset["R3_Notes"] == "Access restrictions.").sum())
        payment_count = int((subset["R3_Notes"] == "Payment restrictions.").sum())
        non_english_count = int((subset["R3_Notes"] == "Non-English literature").sum())

        lines: List[str] = []
        lines.append("[R3_Notes summary for specific restriction-related values where Need_R3 = 'yes']")
        lines.append(f"  'Access restrictions.': {access_count} records")
        lines.append(f"  'Payment restrictions.': {payment_count} records")
        lines.append(f"  'Non-English literature': {non_english_count} records")

        return "\n".join(lines) + "\n"

    def count_final_included(
        self, df: pd.DataFrame
    ) -> Tuple[str, int, Dict[str, Dict[str, List[str]]]]:
        """
        Count the number of finally included studies and list their No. values.

        Final Included conditions:
          (1) R1_Decision = R2_Decision = 'include'
          (2) R1_Decision = R2_Decision = 'unsure' and R3_Decision = 'include'
          (3) R1_Decision ≠ R2_Decision and R3_Decision = 'include'

        :param df: Normalized full result DataFrame.
        :return: (Formatted text, total count, per-subcategory statistics).
        """
        r1_decision = df["R1_Decision"]
        r2_decision = df["R2_Decision"]
        r3_decision = df["R3_Decision"]
        need_r3 = df["Need_R3"]
        no_col = df["No."]

        # (1) R1 = R2 = 'include'
        mask1 = (r1_decision == "include") & (r2_decision == "include")

        # (2) R1 = R2 = 'unsure' and R3 = 'include'
        mask2 = (
            (r1_decision == "unsure")
            & (r2_decision == "unsure")
            & (r3_decision == "include")
            & (need_r3 == "yes")
        )

        # (3) R1 ≠ R2 and R3 = 'include'
        mask3 = (r1_decision != r2_decision) & (r3_decision == "include") & (need_r3 == "yes")

        stats: Dict[str, Dict[str, List[str]]] = {
            "R1=R2=include": {
                "count": int(mask1.sum()),
                "nos": self._extract_no_list(no_col[mask1]),
            },
            "R1=R2=unsure,R3=include": {
                "count": int(mask2.sum()),
                "nos": self._extract_no_list(no_col[mask2]),
            },
            "R1!=R2,R3=include": {
                "count": int(mask3.sum()),
                "nos": self._extract_no_list(no_col[mask3]),
            },
        }
        total = sum(info["count"] for info in stats.values())

        lines: List[str] = []
        lines.append("[Final included studies]")
        lines.append(f"  Total: {total}")
        lines.append(
            f"  (1) R1 = R2 = 'include': {stats['R1=R2=include']['count']} studies, "
            f"No.: [{', '.join(stats['R1=R2=include']['nos'])}]"
        )
        lines.append(
            "  (2) R1 = R2 = 'unsure' and R3 = 'include': "
            f"{stats['R1=R2=unsure,R3=include']['count']} studies, "
            f"No.: [{', '.join(stats['R1=R2=unsure,R3=include']['nos'])}]"
        )
        lines.append(
            "  (3) R1 ≠ R2 and R3 = 'include': "
            f"{stats['R1!=R2,R3=include']['count']} studies, "
            f"No.: [{', '.join(stats['R1!=R2,R3=include']['nos'])}]"
        )

        return "\n".join(lines) + "\n", total, stats

    def count_final_excluded(self, df: pd.DataFrame) -> Tuple[str, int, Dict[str, int]]:
        """
        Count the number of finally excluded studies.

        Final Excluded conditions:
          (1) R1_Decision = R2_Decision = 'exclude'
          (2) R1_Decision = R2_Decision = 'unsure' and R3_Decision = 'exclude'
          (3) R1_Decision ≠ R2_Decision and R3_Decision = 'exclude'

        :param df: Normalized full result DataFrame.
        :return: (Formatted text, total count, per-subcategory counts).
        """
        r1_decision = df["R1_Decision"]
        r2_decision = df["R2_Decision"]
        r3_decision = df["R3_Decision"]
        need_r3 = df["Need_R3"]

        # (1) R1 = R2 = 'exclude'
        mask1 = (r1_decision == "exclude") & (r2_decision == "exclude")

        # (2) R1 = R2 = 'unsure' and R3 = 'exclude'
        mask2 = (
            (r1_decision == "unsure")
            & (r2_decision == "unsure")
            & (r3_decision == "exclude")
            & (need_r3 == "yes")
        )

        # (3) R1 ≠ R2 and R3 = 'exclude'
        mask3 = (r1_decision != r2_decision) & (r3_decision == "exclude") & (need_r3 == "yes")

        counts = {
            "R1=R2=exclude": int(mask1.sum()),
            "R1=R2=unsure,R3=exclude": int(mask2.sum()),
            "R1!=R2,R3=exclude": int(mask3.sum()),
        }
        total = sum(counts.values())

        lines: List[str] = []
        lines.append("[Final excluded studies]")
        lines.append(f"  Total: {total}")
        lines.append(f"  (1) R1 = R2 = 'exclude': {counts['R1=R2=exclude']} studies")
        lines.append(
            "  (2) R1 = R2 = 'unsure' and R3 = 'exclude': "
            f"{counts['R1=R2=unsure,R3=exclude']} studies"
        )
        lines.append(
            "  (3) R1 ≠ R2 and R3 = 'exclude': "
            f"{counts['R1!=R2,R3=exclude']} studies"
        )

        return "\n".join(lines) + "\n", total, counts

    def build_report_text(self, df: pd.DataFrame) -> str:
        """
        Build the full textual report for the three-round screening results.

        :param df: Normalized full result DataFrame.
        :return: Report text.
        """
        lines: List[str] = []
        lines.append("======================================================")
        lines.append("Three-round (R1/R2/R3) screening consistency summary")
        lines.append(f"Data file: {self.input_path}")
        lines.append(f"Total records: {len(df)}")
        lines.append("======================================================")
        lines.append("")

        # 1. R3_Decision distribution for Need_R3 = 'yes'
        r3_decision_text, _ = self.summarize_r3_decision_distribution(df)
        lines.append(r3_decision_text.rstrip())
        lines.append("")

        # 2. R3_Notes counts for specific restriction-related values
        r3_notes_text = self.summarize_r3_restriction_notes(df)
        lines.append(r3_notes_text.rstrip())
        lines.append("")

        # 3. Final included statistics (with No. lists)
        included_text, _, _ = self.count_final_included(df)
        lines.append(included_text.rstrip())
        lines.append("")

        # 4. Final excluded statistics
        excluded_text, _, _ = self.count_final_excluded(df)
        lines.append(excluded_text.rstrip())
        lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def write_report(self, text: str) -> None:
        """
        Write the analysis report to a txt file.

        :param text: Report text.
        :return: None
        """
        try:
            self.output_txt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[INFO] Triple-round screening analysis report written to: {self.output_txt_path}")
        except Exception as e:
            print(f"[ERROR] Failed to write analysis report: {e}")
            sys.exit(1)

    def run(self) -> pd.DataFrame:
        """
        Execute the full analysis pipeline for three-round screening results.

        :return: Normalized full result DataFrame (for downstream use).
        """
        df = self.load_results()
        report_text = self.build_report_text(df)
        print(report_text)
        self.write_report(report_text)
        return df


def main() -> None:
    """
    Script entry point: run the three-round screening result analysis.

    :return: None
    """
    # Assume this script is located under apps/systematic_review/double_blind/
    project_root = Path(__file__).resolve().parents[3]
    base_dir = project_root / "data" / "systematic_review" / "double_blind" / "stage1_title_abstract"

    report_txt_path = base_dir / "triple_blind_consistency_report.txt"

    analyzer = TripleBlindConsistencyAnalyzer(base_dir, report_txt_path)
    try:
        analyzer.run()
    except Exception as e:
            print(f"[ERROR] Triple-round screening analysis failed: {e}")
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()