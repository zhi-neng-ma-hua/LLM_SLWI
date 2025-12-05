# -*- coding: utf-8 -*-
"""
double_blind_consistency.py

Purpose:
    1. Read double-blind screening result files:
         data/systematic_review/double_blind/stage1_title_abstract/R1_analysis_results.xlsx
         data/systematic_review/double_blind/stage1_title_abstract/R2_analysis_results.xlsx
    2. Align R1 and R2 records using Title + Year as a composite key.
    3. Check whether No. is consistent between R1 and R2 for the same Title + Year,
       and report inconsistent records.
    4. Split records into four categories based on the Decision columns:
         (1) R1 = R2 = 'include'
         (2) R1 = R2 = 'exclude'
         (3) R1 = R2 = 'unsure'
         (4) Decision_R1 != Decision_R2
    5. For each category, output only the count (with condition description)
       and the corresponding No. lists (R1 and R2 separately).
    6. Write a complete, human-readable consistency report to a txt file
       in the same directory for easy review.
    7. Merge the aligned R1/R2 results into a single file:
         data/systematic_review/double_blind/stage1_title_abstract/R1_R2_analysis_results.xlsx
       Columns: No., Title, Year, R1_Decision, R1_Notes, R2_Decision, R2_Notes, Need_R3
       Need_R3 is marked "Yes" in the following cases:
         • R1 = R2 = 'unsure'
         • Decision_R1 != Decision_R2
       Otherwise Need_R3 is marked "No".
"""

import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd


class DoubleBlindConsistencyAnalyzer:
    """
    Perform consistency analysis for double-blind screening results.

    :param base_dir: Root directory containing the R1/R2 result files.
    :param output_txt_path: Output path for the consistency report (txt).
    """

    def __init__(self, base_dir: Path, output_txt_path: Path) -> None:
        """
        Initialize the consistency analyzer.

        :param base_dir: Root directory containing R1/R2 analysis result files.
        :param output_txt_path: Output path for the consistency report (txt).
        """
        self.base_dir = base_dir
        self.output_txt_path = output_txt_path
        self.r1_path = self.base_dir / "R1_analysis_results.xlsx"
        self.r2_path = self.base_dir / "R2_analysis_results.xlsx"

    def load_aligned_results(self) -> pd.DataFrame:
        """
        Load R1/R2 result files and align them by Title + Year.

        :return: Merged DataFrame containing No._R1/No._R2, Decision_R1/Decision_R2, etc.
        """
        if not self.r1_path.is_file():
            raise FileNotFoundError(f"R1 result file not found: {self.r1_path}")
        if not self.r2_path.is_file():
            raise FileNotFoundError(f"R2 result file not found: {self.r2_path}")

        r1_df = pd.read_excel(self.r1_path)
        r2_df = pd.read_excel(self.r2_path)

        required_cols = {"Title", "Year", "Decision", "No."}
        missing_r1 = required_cols - set(r1_df.columns)
        missing_r2 = required_cols - set(r2_df.columns)
        if missing_r1:
            raise KeyError(f"R1 file missing required columns: {missing_r1}")
        if missing_r2:
            raise KeyError(f"R2 file missing required columns: {missing_r2}")

        # Normalize Year as string; normalize Decision as lower-case string
        r1_df["Year"] = r1_df["Year"].astype(str).str.strip()
        r2_df["Year"] = r2_df["Year"].astype(str).str.strip()

        r1_df["Decision"] = r1_df["Decision"].astype(str).str.strip().str.lower()
        r2_df["Decision"] = r2_df["Decision"].astype(str).str.strip().str.lower()

        merged_df = pd.merge(
            r1_df,
            r2_df,
            on=["Title", "Year"],
            how="inner",
            suffixes=("_R1", "_R2"),
        )
        return merged_df

    @staticmethod
    def _extract_no_list(series: pd.Series) -> List[str]:
        """
        Extract a list of No. values as strings from a Series.

        :param series: Series of No._R1 or No._R2.
        :return: List of No. values as strings.
        """
        numbers: List[str] = []
        for value in series:
            if pd.isna(value):
                continue
            try:
                numbers.append(str(int(value)))
            except (ValueError, TypeError):
                numbers.append(str(value).strip())
        return numbers

    def _format_no_consistency_section(self, merged_df: pd.DataFrame) -> str:
        """
        Build the text section for No. consistency checking.

        :param merged_df: Aligned merged DataFrame.
        :return: Formatted text section.
        """
        lines: List[str] = []
        lines.append("[No. consistency check (aligned by Title + Year)]")

        if "No._R1" not in merged_df.columns or "No._R2" not in merged_df.columns:
            lines.append(
                "  [Warning] No._R1 or No._R2 columns are missing in merged results. "
                "No. consistency cannot be checked."
            )
            return "\n".join(lines) + "\n"

        no_r1 = merged_df["No._R1"]
        no_r2 = merged_df["No._R2"]
        mismatch_mask = no_r1 != no_r2

        mismatch_df = merged_df[mismatch_mask].copy()
        mismatch_count = len(mismatch_df)

        lines.append(f"  Total aligned samples: {len(merged_df)}")
        lines.append(f"  Count of records with No._R1 = No._R2: {len(merged_df) - mismatch_count}")
        lines.append(f"  Count of records with No._R1 ≠ No._R2: {mismatch_count}")

        if mismatch_count == 0:
            lines.append("  All aligned records have consistent No. values.")
            return "\n".join(lines) + "\n"

        lines.append("  No. mismatch pairs (No._R1 → No._R2):")
        for _, row in mismatch_df.iterrows():
            r1_no = row.get("No._R1", "")
            r2_no = row.get("No._R2", "")
            lines.append(f"    - {r1_no} → {r2_no}")

        return "\n".join(lines) + "\n"

    def split_by_decision(self, merged_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Split aligned results into four subsets based on Decision consistency.

        :param merged_df: Aligned DataFrame containing Decision_R1 / Decision_R2.
        :return: Mapping from category name to subset DataFrame.
        """
        df = merged_df.copy()
        decision_r1 = df["Decision_R1"]
        decision_r2 = df["Decision_R2"]

        both_include_mask = (decision_r1 == "include") & (decision_r2 == "include")
        both_exclude_mask = (decision_r1 == "exclude") & (decision_r2 == "exclude")
        both_unsure_mask = (decision_r1 == "unsure") & (decision_r2 == "unsure")
        mismatch_mask = decision_r1 != decision_r2

        return {
            "both_include": df[both_include_mask],
            "both_exclude": df[both_exclude_mask],
            "both_unsure": df[both_unsure_mask],
            "decision_mismatch": df[mismatch_mask],
        }

    def _format_no_summary(self, condition_text: str, subset_df: pd.DataFrame) -> str:
        """
        Format the count and No. lists for a given Decision condition.

        :param condition_text: Condition description (e.g., "R1 = R2 = 'include'").
        :param subset_df: Subset DataFrame belonging to this category.
        :return: Formatted text section.
        """
        lines: List[str] = []
        lines.append("")
        lines.append(f"  Count ({condition_text}): {len(subset_df)}")

        if subset_df.empty:
            lines.append("  R1 No.: []")
            lines.append("  R2 No.: []")
            return "\n".join(lines) + "\n"

        if "No._R1" in subset_df.columns:
            no_r1_list = self._extract_no_list(subset_df["No._R1"])
            lines.append(f"  R1 No.: [{', '.join(no_r1_list)}]")
        else:
            lines.append("  R1 No.: column not found.")

        if "No._R2" in subset_df.columns:
            no_r2_list = self._extract_no_list(subset_df["No._R2"])
            lines.append(f"  R2 No.: [{', '.join(no_r2_list)}]")
        else:
            lines.append("  R2 No.: column not found.")

        return "\n".join(lines) + "\n"

    def build_report_text(self, merged_df: pd.DataFrame) -> str:
        """
        Build the full text report for double-blind consistency analysis.

        :param merged_df: Aligned merged DataFrame.
        :return: Report text.
        """
        categories = self.split_by_decision(merged_df)

        lines: List[str] = []
        lines.append("======================================================")
        lines.append("Double-blind screening consistency analysis (aligned by Title + Year)")
        lines.append(f"R1 file: {self.r1_path}")
        lines.append(f"R2 file: {self.r2_path}")
        lines.append(f"Aligned sample size: {len(merged_df)}")
        lines.append("======================================================")
        lines.append("")

        # 1. No. consistency check
        lines.append(self._format_no_consistency_section(merged_df).rstrip())
        lines.append("")

        # 2. Decision consistency categories
        condition_map: Dict[str, str] = {
            "both_include": "R1 = R2 = 'include'",
            "both_exclude": "R1 = R2 = 'exclude'",
            "both_unsure": "R1 = R2 = 'unsure'",
            "decision_mismatch": "R1 ≠ R2 (Decision mismatch)",
        }

        for key in ["both_include", "both_exclude", "both_unsure", "decision_mismatch"]:
            lines.append(self._format_no_summary(condition_map[key], categories[key]).rstrip())
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def write_report(self, text: str) -> None:
        """
        Write the consistency analysis report to a txt file.

        :param text: Report text.
        :return: None
        """
        try:
            self.output_txt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_txt_path, "w", encoding="utf-8") as file:
                file.write(text)
            print(f"[INFO] Consistency analysis report written to: {self.output_txt_path}")
        except Exception as exc:
            print(f"[ERROR] Failed to write consistency report: {exc}")
            sys.exit(1)

    def run(self) -> pd.DataFrame:
        """
        Run the consistency analysis: load data, generate report, and write txt file.

        :return: Aligned merged DataFrame (for downstream export).
        """
        merged_df = self.load_aligned_results()
        report_text = self.build_report_text(merged_df)
        print(report_text)
        self.write_report(report_text)
        return merged_df


class DoubleBlindMergedResultExporter:
    """
    Export merged double-blind results (R1_R2_analysis_results.xlsx).

    :param merged_df: Aligned R1/R2 merged DataFrame.
    :param output_xlsx_path: Output file path (xlsx).
    """

    def __init__(self, merged_df: pd.DataFrame, output_xlsx_path: Path) -> None:
        """
        Initialize the exporter.

        :param merged_df: Aligned R1/R2 merged DataFrame.
        :param output_xlsx_path: Output file path (xlsx).
        """
        self.merged_df = merged_df.copy()
        self.output_xlsx_path = output_xlsx_path

    def build_export_dataframe(self) -> pd.DataFrame:
        """
        Build the exportable merged result DataFrame.

        Columns: No., Title, Year, R1_Decision, R1_Notes, R2_Decision, R2_Notes, Need_R3

        Need_R3 = "Yes" if:
          - R1 = R2 = 'unsure', or
          - Decision_R1 != Decision_R2
        Otherwise Need_R3 = "No".

        :return: DataFrame to be exported.
        """
        df = self.merged_df

        export_df = pd.DataFrame()
        # Unified index for merged results, distinct from original No._R1/No._R2,
        # for easier manual review.
        export_df["No."] = range(1, len(df) + 1)
        export_df["Title"] = df["Title"]
        export_df["Year"] = df["Year"]

        # R1 decisions and notes
        export_df["R1_Decision"] = df["Decision_R1"]
        if "Notes_R1" in df.columns:
            export_df["R1_Notes"] = df["Notes_R1"].fillna("").astype(str)
        else:
            export_df["R1_Notes"] = ""

        # R2 decisions and notes
        export_df["R2_Decision"] = df["Decision_R2"]
        if "Notes_R2" in df.columns:
            export_df["R2_Notes"] = df["Notes_R2"].fillna("").astype(str)
        else:
            export_df["R2_Notes"] = ""

        # Need_R3: Yes if R1 = R2 = 'unsure' or Decision_R1 != Decision_R2, otherwise No
        dec_r1 = df["Decision_R1"]
        dec_r2 = df["Decision_R2"]
        need_r3_mask = ((dec_r1 == "unsure") & (dec_r2 == "unsure")) | (dec_r1 != dec_r2)
        export_df["Need_R3"] = need_r3_mask.map({True: "Yes", False: "No"})

        return export_df

    def export(self) -> None:
        """
        Export merged results to R1_R2_analysis_results.xlsx.

        :return: None
        """
        export_df = self.build_export_dataframe()
        try:
            self.output_xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            export_df.to_excel(self.output_xlsx_path, index=False)
            print(f"[INFO] Merged results exported to: {self.output_xlsx_path}")
        except Exception as exc:
            print(f"[ERROR] Failed to export merged results: {exc}")
            sys.exit(1)


def main() -> None:
    """
    Script entry point: run consistency analysis and export merged R1/R2 results.

    :return: None
    """
    # Assume this script is located under apps/systematic_review/double_blind/
    project_root = Path(__file__).resolve().parents[3]
    base_dir = project_root / "data" / "systematic_review" / "double_blind" / "stage1_title_abstract"

    consistency_txt_path = base_dir / "double_blind_consistency_report.txt"
    merged_xlsx_path = base_dir / "R1_R2_analysis_results.xlsx"

    analyzer = DoubleBlindConsistencyAnalyzer(base_dir, consistency_txt_path)
    try:
        merged_df = analyzer.run()
    except Exception as exc:
        print(f"[ERROR] Consistency analysis failed: {exc}")
        sys.exit(1)

    exporter = DoubleBlindMergedResultExporter(merged_df, merged_xlsx_path)
    exporter.export()

    sys.exit(0)


if __name__ == "__main__":
    main()
