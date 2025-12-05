# -*- coding: utf-8 -*-
"""
stage2_full_text_final_included_merger.py

Stage 2 (Full-text) R1/R2/R3 screening results – final inclusion statistics and export tool.

Main functions:
1. Read the Stage 2 results file:
   data/systematic_review/double_blind/stage2_full_text/R1_R2_R3_analysis_results.xlsx
2. After normalizing decision columns, classify finally included studies and collect No. lists for each category:
   (1) R1_Decision = R2_Decision = "include"
   (2) R1_Decision = R2_Decision = "unsure" AND R3_Decision = "include"
   (3) R1_Decision ≠ R2_Decision AND R3_Decision = "include"
3. Check records where R3_Decision is missing and output No. lists for:
   (1) R1_Decision = R2_Decision = "unsure" AND R3_Decision is blank
   (2) R1_Decision ≠ R2_Decision AND R3_Decision is blank
4. Count records with Remark = "Access restrictions" (case-insensitive, with or without trailing period) and output their No. lists.
5. Count finally excluded records and, among them, count those with Remark = "Access restrictions".
6. Write all finally included studies (union of the three include categories) to:
   data/systematic_review/double_blind/stage2_full_text/R1_R2_R3_final_included_studies.xlsx
7. Write a concise and structured TXT summary report to:
   data/systematic_review/double_blind/stage2_full_text/R1_R2_R3_final_included_summary.txt

Author: Aiden Cao <zhinengmahua@gmail.com>
Date: 2025-07-13
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from apps.systematic_review.utils.logger_manager import LoggerManager

PathLike = Union[str, Path]

# Normalized value in Remark column that is treated as "access restrictions"
ACCESS_RESTRICTIONS_VALUE = "access restrictions"


def setup_logger(
    name: str = "stage2_full_text_final_included_merger",
    verbose: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger.
    :param name: Logger name
    :param verbose: Whether to enable DEBUG level logging
    :return: logging.Logger instance
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class Stage2FullTextFinalInclusionAnalyzer:
    """
    Controller for final inclusion statistics and export of Stage 2 Full-text R1/R2/R3 results.
    """

    INPUT_FILENAME = "R1_R2_R3_analysis_results.xlsx"
    OUTPUT_FILENAME = "R1_R2_R3_final_included_studies.xlsx"
    SUMMARY_FILENAME = "R1_R2_R3_final_included_summary.txt"

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the analyzer, resolve paths, and set up logging.
        :param logger: Logger instance; if None, a default logger is created
        """
        self.logger = logger or setup_logger()
        self._init_paths()

    def _init_paths(self) -> None:
        """
        Initialize and validate input/output paths.
        """
        # Current file path: apps/systematic_review/double_blind/stage2_full_text/xxx.py
        project_root = Path(__file__).resolve().parents[4]
        stage_root = (
            project_root
            / "data"
            / "systematic_review"
            / "double_blind"
            / "stage2_full_text"
        )

        self.stage_root = stage_root
        self.input_path = stage_root / self.INPUT_FILENAME
        self.output_path = stage_root / self.OUTPUT_FILENAME
        self.summary_path = stage_root / self.SUMMARY_FILENAME

        if not self.input_path.is_file():
            raise FileNotFoundError(f"Analysis results file not found: {self.input_path}")

        self.logger.info(
            f"[PATH] Input file: {self.input_path} | Output file: {self.output_path} | Summary report: {self.summary_path}"
        )

    @staticmethod
    def _normalize_decision_column(series: pd.Series) -> pd.Series:
        """
        Normalize decision columns: convert to lowercase string and strip whitespace.
        """
        return series.astype(str).str.strip().str.lower()

    @staticmethod
    def _normalize_remark_column(series: pd.Series) -> pd.Series:
        """
        Normalize Remark column: strip whitespace, remove trailing periods, and lowercase.
        """
        return (
            series.astype(str)
            .str.strip()
            .str.rstrip(".")
            .str.lower()
        )

    @staticmethod
    def _is_blank(series: pd.Series) -> pd.Series:
        """
        Determine whether decision values are blank (NaN/None/empty/whitespace/'nan' string).
        """
        return series.isnull() | (
            series.astype(str).str.strip().replace("nan", "") == ""
        )

    @staticmethod
    def _extract_no_list(series: pd.Series) -> List[str]:
        """
        Extract a list of No. values as strings.
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

    def load_results(self) -> pd.DataFrame:
        """
        Read and normalize Stage 2 results data.
        :return: DataFrame with normalized decision helper columns
        """
        df = pd.read_excel(self.input_path, dtype=str).fillna("")
        if "No." not in df.columns:
            self.logger.warning("[WARN] Input file is missing 'No.' column; some lists may be empty.")

        # Normalize decision columns
        for col in ("R1_Decision", "R2_Decision", "R3_Decision"):
            if col not in df.columns:
                raise KeyError(f"Input file is missing required decision column: {col}")
        df["_R1"] = self._normalize_decision_column(df["R1_Decision"])
        df["_R2"] = self._normalize_decision_column(df["R2_Decision"])
        df["_R3"] = self._normalize_decision_column(df["R3_Decision"])

        return df

    def classify_final_included(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Classify finally included studies into three categories and return counts and No. lists.
        :param df: Normalized DataFrame
        :return: dict where each category has keys: mask / count / nos
        """
        r1 = df["_R1"]
        r2 = df["_R2"]
        r3 = df["_R3"]

        mask_cat1 = (r1 == "include") & (r2 == "include")
        mask_cat2 = (r1 == "unsure") & (r2 == "unsure") & (r3 == "include")
        mask_cat3 = (r1 != r2) & (r3 == "include")

        stats: Dict[str, Dict[str, Any]] = {}

        def _make_stat(key: str, mask: pd.Series, label: str) -> None:
            count = int(mask.sum())
            if "No." in df.columns:
                nos = self._extract_no_list(df.loc[mask, "No."])
            else:
                nos = []
            self.logger.info(f"[STATS] {label}: {count} records")
            if nos:
                self.logger.info(f"[No.] {label} No. list: {nos}")
            stats[key] = {"mask": mask, "count": count, "nos": nos}

        _make_stat("cat1", mask_cat1, "(1) R1 = R2 = include")
        _make_stat("cat2", mask_cat2, "(2) R1 = R2 = unsure, R3 = include")
        _make_stat("cat3", mask_cat3, "(3) R1 ≠ R2, R3 = include")

        return stats

    def check_missing_r3(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Check records with missing R3_Decision under:
        1) R1_Decision = R2_Decision = 'unsure' and R3_Decision is blank
        2) R1_Decision ≠ R2_Decision and R3_Decision is blank
        :param df: Normalized DataFrame
        :return: dict with counts and No. lists for each missing category
        """
        r1 = df["_R1"]
        r2 = df["_R2"]
        r3_blank = self._is_blank(df["R3_Decision"])

        mask_unsure_both = (r1 == "unsure") & (r2 == "unsure") & r3_blank
        mask_diff = (r1 != r2) & r3_blank

        stats: Dict[str, Dict[str, Any]] = {}

        def _make_stat(key: str, mask: pd.Series, label: str) -> None:
            count = int(mask.sum())
            self.logger.info(f"[CHECK] {label}: {count} records")
            nos: List[str] = []
            if "No." in df.columns and count > 0:
                nos = self._extract_no_list(df.loc[mask, "No."])
                self.logger.warning(f"[No.] {label} No. list: {nos}")
            stats[key] = {"count": count, "nos": nos}

        _make_stat("unsure_no_r3", mask_unsure_both, "R1 = R2 = unsure and R3 is missing")
        _make_stat("diff_no_r3", mask_diff, "R1 ≠ R2 and R3 is missing")

        return stats

    def count_access_restrictions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Count records where Remark is "Access restrictions" (case-insensitive; trailing period ignored).
        :param df: Normalized DataFrame
        :return: dict with mask, count, and No. list
        """
        if "Remark" not in df.columns:
            self.logger.warning("[STATS] Input file is missing Remark column; skipping Access restrictions statistics.")
            return {"mask": pd.Series(False, index=df.index), "count": 0, "nos": []}

        remark_norm = self._normalize_remark_column(df["Remark"])
        mask = remark_norm == ACCESS_RESTRICTIONS_VALUE
        count = int(mask.sum())
        self.logger.info(
            f"[STATS] Remark = 'Access restrictions' (case/period-insensitive) count: {count}"
        )

        nos: List[str] = []
        if count > 0 and "No." in df.columns:
            nos = self._extract_no_list(df.loc[mask, "No."])
            self.logger.info(
                f"[No.] Remark = 'Access restrictions' No. list: {nos}"
            )

        return {"mask": mask, "count": count, "nos": nos}

    @staticmethod
    def _reorder_columns_for_output(df: pd.DataFrame) -> pd.DataFrame:
        """
        Optionally define the final column order for export.
        Currently returns the DataFrame unchanged (original column order).
        """
        return df

    def write_final_included(self, df: pd.DataFrame, final_mask: pd.Series) -> None:
        """
        Export finally included studies to an Excel file.
        :param df: Original DataFrame
        :param final_mask: Boolean mask indicating final inclusion
        """
        final_df = df.loc[final_mask].copy()
        final_df = self._reorder_columns_for_output(final_df)

        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_excel(self.output_path, index=False)
        self.logger.info(
            f"[EXPORT] Final included studies written to: {self.output_path} | Rows: {len(final_df)}"
        )

    def _build_summary_text(
        self,
        total_count: int,
        final_stats: Dict[str, Dict[str, Any]],
        excluded_count: int,
        access_stats: Dict[str, Any],
        access_excluded_stats: Dict[str, Any],
        missing_r3_stats: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        Build the TXT summary report text.
        :return: Summary report as a string
        """
        lines: List[str] = []

        lines.append("=" * 58)
        lines.append("Stage 2 Full-text – Final Inclusion Summary")
        lines.append("=" * 58)
        lines.append("")

        # 1. Overall counts
        lines.append("1. Overall counts")
        lines.append(f"- Total records                   : {total_count}")
        lines.append(
            f"- Final included (any category)   : {final_stats['total']['count']}"
        )
        lines.append(f"- Final excluded                  : {excluded_count}")
        lines.append("")

        # 2. Final inclusion categories
        lines.append("2. Final inclusion categories")
        lines.append(
            f"- (1) R1 = R2 = include              : {final_stats['cat1']['count']}"
        )
        lines.append(
            f"- (2) R1 = R2 = unsure, R3 = include : {final_stats['cat2']['count']}"
        )
        lines.append(
            f"- (3) R1 ≠ R2, R3 = include          : {final_stats['cat3']['count']}"
        )
        lines.append("")

        # 3. R3 missing checks
        lines.append("3. R3 missing checks")
        lines.append(
            f"- R1 = R2 = unsure, R3 missing : {missing_r3_stats['unsure_no_r3']['count']}"
        )
        lines.append(
            f"- R1 ≠ R2, R3 missing          : {missing_r3_stats['diff_no_r3']['count']}"
        )
        lines.append("")

        # 4. Access restrictions
        lines.append("4. Access restrictions (Remark)")
        lines.append(
            f"- All records with Remark = 'Access restrictions'     : {access_stats['count']}"
        )
        lines.append(
            f"- Excluded records with Remark = 'Access restrictions': {access_excluded_stats['count']}"
        )
        lines.append("")

        # 5. No. lists (if available)
        lines.append("5. No. lists (if available)")
        if final_stats["cat1"]["nos"]:
            lines.append(
                f"- Final included (1) R1 = R2 = include              : {final_stats['cat1']['nos']}"
            )
        if final_stats["cat2"]["nos"]:
            lines.append(
                f"- Final included (2) R1 = R2 = unsure, R3 = include : {final_stats['cat2']['nos']}"
            )
        if final_stats["cat3"]["nos"]:
            lines.append(
                f"- Final included (3) R1 ≠ R2, R3 = include          : {final_stats['cat3']['nos']}"
            )
        if missing_r3_stats["unsure_no_r3"]["nos"]:
            lines.append(
                f"- R1 = R2 = unsure, R3 missing                     : {missing_r3_stats['unsure_no_r3']['nos']}"
            )
        if missing_r3_stats["diff_no_r3"]["nos"]:
            lines.append(
                f"- R1 ≠ R2, R3 missing                              : {missing_r3_stats['diff_no_r3']['nos']}"
            )
        if access_stats["nos"]:
            lines.append(
                f"- All Access restrictions                          : {access_stats['nos']}"
            )
        if access_excluded_stats["nos"]:
            lines.append(
                f"- Excluded Access restrictions                     : {access_excluded_stats['nos']}"
            )

        if (
            not final_stats["cat1"]["nos"]
            and not final_stats["cat2"]["nos"]
            and not final_stats["cat3"]["nos"]
            and not missing_r3_stats["unsure_no_r3"]["nos"]
            and not missing_r3_stats["diff_no_r3"]["nos"]
            and not access_stats["nos"]
            and not access_excluded_stats["nos"]
        ):
            lines.append("- Column 'No.' is missing or empty; No. lists not printed.")

        lines.append("")
        lines.append("=" * 58)
        return "\n".join(lines)

    def _write_summary(self, text: str) -> None:
        """
        Write the summary text to a TXT file.
        :param text: Summary report text
        """
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.summary_path, "w", encoding="utf-8") as f:
            f.write(text)
        self.logger.info(f"[SUMMARY] Statistics written to TXT report: {self.summary_path}")

    def run(self) -> None:
        """
        Main pipeline:
        Load data → classify final inclusion → compute exclusions →
        check missing R3 → count Access restrictions → export final included → write TXT summary.
        """
        df = self.load_results()
        total_count = len(df)

        # 1. Final inclusion classification and No. lists
        final_stats = self.classify_final_included(df)
        included_mask = (
            final_stats["cat1"]["mask"]
            | final_stats["cat2"]["mask"]
            | final_stats["cat3"]["mask"]
        )
        included_count = int(included_mask.sum())
        excluded_mask = ~included_mask
        excluded_count = int(excluded_mask.sum())
        final_stats["total"] = {"mask": included_mask, "count": included_count}

        self.logger.info(f"[STATS] Final included studies: {included_count}")
        self.logger.info(f"[STATS] Final excluded studies: {excluded_count}")

        # 2. R3_Decision missing checks
        missing_r3_stats = self.check_missing_r3(df)

        # 3. Remark = Access restrictions (all records)
        access_stats = self.count_access_restrictions(df)

        # 4. Remark = Access restrictions among finally excluded
        if access_stats["count"] > 0 and "Remark" in df.columns:
            remark_norm = self._normalize_remark_column(df["Remark"])
            access_mask_all = remark_norm == ACCESS_RESTRICTIONS_VALUE
            access_excluded_mask = access_mask_all & excluded_mask
            access_excluded_count = int(access_excluded_mask.sum())
            access_excluded_nos: List[str] = []
            if access_excluded_count > 0 and "No." in df.columns:
                access_excluded_nos = self._extract_no_list(df.loc[access_excluded_mask, "No."])
            access_excluded_stats = {
                "count": access_excluded_count,
                "nos": access_excluded_nos,
            }
            self.logger.info(
                f"[STATS] Remark = 'Access restrictions' and finally excluded: {access_excluded_count}"
            )
        else:
            access_excluded_stats = {"count": 0, "nos": []}

        # 5. Export final included studies
        self.write_final_included(df, included_mask)

        # 6. Build and write TXT summary report
        summary_text = self._build_summary_text(
            total_count=total_count,
            final_stats=final_stats,
            excluded_count=excluded_count,
            access_stats=access_stats,
            access_excluded_stats=access_excluded_stats,
            missing_r3_stats=missing_r3_stats,
        )
        self._write_summary(summary_text)


def main() -> None:
    """
    Main entry point: run Stage 2 Full-text final inclusion and exclusion statistics and export.
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] Stage 2 Full-text final inclusion summary started")

    analyzer = Stage2FullTextFinalInclusionAnalyzer(logger=logger)
    analyzer.run()

    logger.info("[MAIN] Stage 2 Full-text final inclusion summary finished")


if __name__ == "__main__":
    main()