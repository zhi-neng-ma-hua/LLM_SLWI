# -*- coding: utf-8 -*-
"""
triple_blind_consistency.py

Purpose
-------
Based on the three-round screening result file:
    data/systematic_review/double_blind/stage1_title_abstract/R1_R2_R3_analysis_results.xlsx

This script performs the following tasks:

1. For records with Need_R3 = "yes", summarize the distribution of R3_Decision.
2. For records with Need_R3 = "yes", count how many rows in R3_Notes are:
     - "Access restrictions."
     - "Payment restrictions."
     - "Non-English literature"
3. Count finally included studies (Final Included) under the following rules:
     (1) R1_Decision = R2_Decision = "include"
     (2) R1_Decision = R2_Decision = "unsure" and R3_Decision = "include"
     (3) R1_Decision ≠ R2_Decision and R3_Decision = "include"
   For each rule, output the No. list for manual inspection, and export all
   finally included studies to a dedicated Excel file:
   - rows: final-included records only
   - columns: all original columns
   - NaN and literal "nan"/"NaN" values replaced with "" for cleaner display.
4. Count finally excluded studies (Final Excluded) under analogous rules with
   R3_Decision = "exclude".
5. Print all results to the terminal and write them to a txt report file.

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

    Parameters
    ----------
    base_dir : Path
        Root directory containing R1_R2_R3_analysis_results.xlsx.
    output_txt_path : Path
        Output path for the summary report (txt).
    """

    # Required columns for the analysis
    REQUIRED_COLUMNS = {
        "No.",
        "Title",
        "Year",
        "R1_Decision",
        "R2_Decision",
        "R3_Decision",
        "R3_Notes",
        "Need_R3",
    }

    # Decision-related columns to be normalized as lower-case strings
    DECISION_COLUMNS = ["R1_Decision", "R2_Decision", "R3_Decision", "Need_R3"]

    # R3_Notes values of special interest
    NOTE_ACCESS = "Access restrictions."
    NOTE_PAYMENT = "Payment restrictions."
    NOTE_NON_ENGLISH = "Non-English literature"

    def __init__(self, base_dir: Path, output_txt_path: Path) -> None:
        """
        Initialize the analyzer.

        Parameters
        ----------
        base_dir : Path
            Root directory containing result files.
        output_txt_path : Path
            Output path for the summary report (txt).
        """
        self.base_dir = base_dir
        self.output_txt_path = output_txt_path

        # Input: three-round screening result file
        self.input_path = self.base_dir / "R1_R2_R3_analysis_results.xlsx"

        # Output: final included studies (all columns, final-included rows only)
        self.final_included_output_path = (
            self.base_dir / "R1_R2_R3_final_included_studies.xlsx"
        )

    # ------------------------------------------------------------------
    # Data loading and normalization
    # ------------------------------------------------------------------
    def load_results(self) -> pd.DataFrame:
        """
        Load and normalize the three-round screening results.

        Steps
        -----
        1. Read the Excel file from self.input_path.
        2. Verify that all REQUIRED_COLUMNS are present.
        3. Normalize decision-related fields (non-missing values only):
           - cast to string
           - strip whitespace
           - convert to lower case
        4. Normalize Year as string and strip whitespace.
        5. Normalize R3_Notes as string and fill missing values with "".

        Returns
        -------
        pd.DataFrame
            Normalized result DataFrame.
        """
        if not self.input_path.is_file():
            raise FileNotFoundError(f"Result file not found: {self.input_path}")

        df = pd.read_excel(self.input_path)

        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise KeyError(f"Result file is missing required columns: {missing}")

        # Normalize decision and Need_R3 fields on non-null values only
        for col in self.DECISION_COLUMNS:
            series = df[col]
            mask = series.notna()
            df.loc[mask, col] = (
                series[mask].astype(str).str.strip().str.lower()
            )

        # Normalize Year as string
        df["Year"] = df["Year"].astype(str).str.strip()

        # Normalize R3_Notes as text and ensure no NaN for subsequent matching
        df["R3_Notes"] = df["R3_Notes"].fillna("").astype(str)

        return df

    # ------------------------------------------------------------------
    # Helper functions
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_no_list(series: pd.Series) -> List[str]:
        """
        Convert values from the "No." column into a clean list of strings.

        Parameters
        ----------
        series : pd.Series
            Series corresponding to the "No." column.

        Returns
        -------
        List[str]
            List of No. values converted to strings.
        """
        nos: List[str] = []
        for value in series:
            if pd.isna(value):
                continue
            try:
                # Avoid "1.0" style strings for numeric No.
                nos.append(str(int(value)))
            except (ValueError, TypeError):
                nos.append(str(value).strip())
        return nos

    # ------------------------------------------------------------------
    # R3 summary statistics
    # ------------------------------------------------------------------
    def summarize_r3_decision_distribution(
        self, df: pd.DataFrame
    ) -> Tuple[str, Dict[str, int]]:
        """
        Summarize R3_Decision distribution where Need_R3 = 'yes'.

        Parameters
        ----------
        df : pd.DataFrame
            Full result DataFrame.

        Returns
        -------
        Tuple[str, Dict[str, int]]
            Formatted text summary and counts dictionary.
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
        Count specific R3_Notes values where Need_R3 = 'yes'.

        Tracked notes
        -------------
        - "Access restrictions."
        - "Payment restrictions."
        - "Non-English literature"

        Parameters
        ----------
        df : pd.DataFrame
            Full result DataFrame.

        Returns
        -------
        str
            Formatted text summary.
        """
        mask_need_r3 = df["Need_R3"] == "yes"
        subset = df[mask_need_r3]

        access_count = int((subset["R3_Notes"] == self.NOTE_ACCESS).sum())
        payment_count = int((subset["R3_Notes"] == self.NOTE_PAYMENT).sum())
        non_english_count = int(
            (subset["R3_Notes"] == self.NOTE_NON_ENGLISH).sum()
        )

        lines: List[str] = []
        lines.append(
            "[R3_Notes summary for specific restriction-related values where Need_R3 = 'yes']"
        )
        lines.append(f"  '{self.NOTE_ACCESS}': {access_count} records")
        lines.append(f"  '{self.NOTE_PAYMENT}': {payment_count} records")
        lines.append(f"  '{self.NOTE_NON_ENGLISH}': {non_english_count} records")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Final-included export
    # ------------------------------------------------------------------
    def _export_final_included(
        self, df: pd.DataFrame, included_mask: pd.Series
    ) -> None:
        """
        Export all finally included studies to an Excel file.

        Behavior
        --------
        - Rows: only records with included_mask == True (final included).
        - Columns: all original columns.
        - NaN values and literal "nan"/"NaN" cells are replaced with ""
          before export for cleaner Excel display.

        Parameters
        ----------
        df : pd.DataFrame
            Normalized full result DataFrame.
        included_mask : pd.Series
            Boolean mask selecting finally included rows.
        """
        # Final included rows, with all original columns
        included_df = df.loc[included_mask].copy()

        # Replace true NaN values with empty strings
        included_df = included_df.fillna("")

        # Replace cells whose entire content is "nan"/"NaN" (with optional whitespace)
        # to also be treated as empty
        included_df = included_df.replace(
            to_replace=r"^\s*nan\s*$",
            value="",
            regex=True,
        )

        try:
            self.final_included_output_path.parent.mkdir(parents=True, exist_ok=True)
            included_df.to_excel(self.final_included_output_path, index=False)
            print(
                f"[INFO] Final included studies exported to: "
                f"{self.final_included_output_path}"
            )
        except Exception as exc:
            print(
                f"[ERROR] Failed to export final included studies: {exc}",
            )

    # ------------------------------------------------------------------
    # Final-included / final-excluded statistics
    # ------------------------------------------------------------------
    def count_final_included(
        self, df: pd.DataFrame
    ) -> Tuple[str, int, Dict[str, Dict[str, List[str]]]]:
        """
        Count finally included studies and list their No. values.

        Final Included conditions
        -------------------------
          (1) R1_Decision = R2_Decision = "include"
          (2) R1_Decision = R2_Decision = "unsure" and R3_Decision = "include"
          (3) R1_Decision ≠ R2_Decision and R3_Decision = "include"

        Parameters
        ----------
        df : pd.DataFrame
            Normalized full result DataFrame.

        Returns
        -------
        Tuple[str, int, Dict[str, Dict[str, List[str]]]]
            Formatted text, total count, and per-subcategory statistics.
        """
        r1_decision = df["R1_Decision"]
        r2_decision = df["R2_Decision"]
        r3_decision = df["R3_Decision"]
        need_r3 = df["Need_R3"]
        no_col = df["No."]

        # (1) R1 = R2 = "include"
        mask_include_agree = (r1_decision == "include") & (r2_decision == "include")

        # (2) R1 = R2 = "unsure" and R3 = "include"
        mask_unsure_then_include = (
            (r1_decision == "unsure")
            & (r2_decision == "unsure")
            & (r3_decision == "include")
            & (need_r3 == "yes")
        )

        # (3) R1 ≠ R2 and R3 = "include"
        mask_disagree_then_include = (
            (r1_decision != r2_decision)
            & (r3_decision == "include")
            & (need_r3 == "yes")
        )

        # Combined mask for all finally included studies
        final_included_mask = (
            mask_include_agree | mask_unsure_then_include | mask_disagree_then_include
        )

        stats: Dict[str, Dict[str, List[str]]] = {
            "R1=R2=include": {
                "count": int(mask_include_agree.sum()),
                "nos": self._extract_no_list(no_col[mask_include_agree]),
            },
            "R1=R2=unsure,R3=include": {
                "count": int(mask_unsure_then_include.sum()),
                "nos": self._extract_no_list(no_col[mask_unsure_then_include]),
            },
            "R1!=R2,R3=include": {
                "count": int(mask_disagree_then_include.sum()),
                "nos": self._extract_no_list(no_col[mask_disagree_then_include]),
            },
        }
        total = sum(info["count"] for info in stats.values())

        # Export final-included rows only (all columns, no NaN/"nan" in Excel)
        self._export_final_included(df, final_included_mask)

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
        Count finally excluded studies.

        Final Excluded conditions
        -------------------------
          (1) R1_Decision = R2_Decision = "exclude"
          (2) R1_Decision = R2_Decision = "unsure" and R3_Decision = "exclude"
          (3) R1_Decision ≠ R2_Decision and R3_Decision = "exclude"

        Parameters
        ----------
        df : pd.DataFrame
            Normalized full result DataFrame.

        Returns
        -------
        Tuple[str, int, Dict[str, int]]
            Formatted text, total count, and per-subcategory counts.
        """
        r1_decision = df["R1_Decision"]
        r2_decision = df["R2_Decision"]
        r3_decision = df["R3_Decision"]
        need_r3 = df["Need_R3"]

        # (1) R1 = R2 = "exclude"
        mask_exclude_agree = (r1_decision == "exclude") & (r2_decision == "exclude")

        # (2) R1 = R2 = "unsure" and R3 = "exclude"
        mask_unsure_then_exclude = (
            (r1_decision == "unsure")
            & (r2_decision == "unsure")
            & (r3_decision == "exclude")
            & (need_r3 == "yes")
        )

        # (3) R1 ≠ R2 and R3 = "exclude"
        mask_disagree_then_exclude = (
            (r1_decision != r2_decision)
            & (r3_decision == "exclude")
            & (need_r3 == "yes")
        )

        counts = {
            "R1=R2=exclude": int(mask_exclude_agree.sum()),
            "R1=R2=unsure,R3=exclude": int(mask_unsure_then_exclude.sum()),
            "R1!=R2,R3=exclude": int(mask_disagree_then_exclude.sum()),
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

    # ------------------------------------------------------------------
    # Report building and writing
    # ------------------------------------------------------------------
    def build_report_text(self, df: pd.DataFrame) -> str:
        """
        Build the full textual report for the three-round screening results.

        Parameters
        ----------
        df : pd.DataFrame
            Normalized full result DataFrame.

        Returns
        -------
        str
            Full report text.
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

        Parameters
        ----------
        text : str
            Report text.
        """
        try:
            self.output_txt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(
                f"[INFO] Triple-round screening analysis report written to: "
                f"{self.output_txt_path}"
            )
        except Exception as exc:
            print(f"[ERROR] Failed to write analysis report: {exc}")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------
    def run(self) -> pd.DataFrame:
        """
        Execute the full analysis pipeline for three-round screening results.

        Steps
        -----
        1. Load and normalize the data.
        2. Build the textual report and print it to stdout.
        3. Write the report to a txt file.
        4. Return the normalized DataFrame for downstream use.

        Returns
        -------
        pd.DataFrame
            Normalized full result DataFrame.
        """
        df = self.load_results()
        report_text = self.build_report_text(df)
        print(report_text)
        self.write_report(report_text)
        return df


def main() -> None:
    """
    Script entry point: run the three-round screening result analysis.

    Assumes this script is located under:
        apps/systematic_review/double_blind/

    The project root is inferred by going up four directory levels
    from the current file.
    """
    project_root = Path(__file__).resolve().parents[4]
    base_dir = (
        project_root
        / "data"
        / "systematic_review"
        / "double_blind"
        / "stage1_title_abstract"
    )

    report_txt_path = base_dir / "triple_blind_consistency_report.txt"

    analyzer = TripleBlindConsistencyAnalyzer(base_dir, report_txt_path)
    try:
        analyzer.run()
    except Exception as exc:
        print(f"[ERROR] Triple-round screening analysis failed: {exc}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()