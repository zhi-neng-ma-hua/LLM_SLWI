# -*- coding: utf-8 -*-
"""
quality_assessment_analysis.py

Purpose
-------
Analyze quality assessment data stored in quality_assessment_table.xlsx,
summarize missingness and value distributions of key fields, and write the
results into a structured TXT report.

Core Functionality
------------------
1. Read sheet "Quality_Assessment_Data" (main quality assessment table).
2. For each column, summarize missingness (treat empty string / whitespace /
   'NR' / 'NA' as missing) and list the No. values for rows containing 'NR'/'NA'.
3. For the following four fields, compute value distributions:
      - total_quality_score
      - quality_category
      - include_in_main_synthesis
      - include_in_meta_analysis
   For each distinct value, report count, percentage, and the list of No. values.
4. Write all summary results to:
   data/systematic_review/quality_assessment/quality_assessment_summary.txt

Author: Aiden Cao <zhinengmahua@gmail.com>
Date: 2025-07-13
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from apps.systematic_review.utils.logger_manager import LoggerManager


def setup_logger(name: str = "quality_assessment_analysis", verbose: bool = True) -> logging.Logger:
    """
    Configure the logger used to record information, warnings, and errors.

    :param name: Logger name.
    :param verbose: Whether to enable verbose DEBUG logging.
    :return: A configured logging.Logger instance.
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class QualityAssessmentAnalyzer:
    """
    Controller for analyzing the quality assessment results table.

    Responsibilities:
    - Resolve paths and load the Excel data.
    - Summarize column-wise missingness.
    - Summarize value distributions for key quality fields.
    - Build a text report and write it to a .txt file.
    """

    INPUT_FILENAME = "quality_assessment_table.xlsx"
    SHEET_NAME = "Quality_Assessment_Data"
    SUMMARY_FILENAME = "quality_assessment_summary.txt"
    NO_COL = "No."  # Primary key column name

    CORE_STATS_COLUMNS: List[str] = [
        "total_quality_score",
        "quality_category",
        "include_in_main_synthesis",
        "include_in_meta_analysis",
    ]

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the analyzer: configure logger, resolve paths, and load data.

        :param logger: Optional logger instance; if None, a default logger is used.
        """
        self.logger = logger or setup_logger()
        self._init_paths()
        self.df = self._load_data()

    def _init_paths(self) -> None:
        """
        Resolve and validate input/output paths.

        :return: None
        :raises FileNotFoundError: If the input Excel file does not exist.
        """
        project_root = Path(__file__).resolve().parents[3]
        base_data_dir = project_root / "data" / "systematic_review" / "quality_assessment"

        self.input_path = base_data_dir / self.INPUT_FILENAME
        self.summary_path = base_data_dir / self.SUMMARY_FILENAME

        if not self.input_path.is_file():
            self.logger.error(f"[ERROR] Input file does not exist: {self.input_path}")
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        self.logger.info(
            f"[PATH] Input file: {self.input_path} | Summary report output: {self.summary_path}"
        )

    def _load_data(self) -> pd.DataFrame:
        """
        Load Excel data from the specified sheet.

        :return: DataFrame containing the main quality assessment table.
        :raises Exception: Propagates any exceptions raised while reading the file.
        """
        try:
            df = pd.read_excel(self.input_path, sheet_name=self.SHEET_NAME)
            self.logger.info(
                f"[INFO] Data loaded successfully: {self.input_path} | "
                f"rows={len(df)}, columns={len(df.columns)}"
            )
            return df
        except Exception as exc:
            self.logger.error(
                f"[ERROR] Failed to read Excel file: {self.input_path} | Error: {exc}"
            )
            raise

    @staticmethod
    def _normalize_missing(series: pd.Series) -> pd.Series:
        """
        Normalize missing values within a column.

        Treat the following as missing (pd.NA):
        - empty string
        - whitespace-only strings
        - 'NR'
        - 'NA'

        :param series: Original column (pd.Series).
        :return: Column with standardized missing values as pd.NA.
        """
        cleaned = series.replace(r"^\s*$", "", regex=True)
        return cleaned.replace(["NR", "NA", ""], pd.NA)

    def _get_missing_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Compute missingness statistics for each column and track 'NR'/'NA' rows.

        For each column, return:
        - missing_count: number of missing entries (after normalization).
        - missing_percentage: percentage of missing entries.
        - nr_na_count: number of entries equal to 'NR' or 'NA'.
        - nr_na_no_list: list of No. values for rows where the column is 'NR'/'NA'.

        :return: Dictionary keyed by column name with missingness statistics.
        """
        stats: Dict[str, Dict[str, Any]] = {}
        total_rows = len(self.df)

        for col in self.df.columns:
            normalized = self._normalize_missing(self.df[col])
            missing_mask = normalized.isna()
            missing_count = int(missing_mask.sum())
            missing_pct = (missing_count / total_rows * 100.0) if total_rows > 0 else 0.0

            nr_na_mask = self.df[col].isin(["NR", "NA"])
            nr_na_count = int(nr_na_mask.sum())
            nr_na_no_list = self.df.loc[nr_na_mask, self.NO_COL].tolist()

            stats[col] = {
                "missing_count": missing_count,
                "missing_percentage": missing_pct,
                "nr_na_count": nr_na_count,
                "nr_na_no_list": nr_na_no_list,
            }

        return stats

    def _get_value_stats(self, columns: List[str]) -> Dict[str, Dict[Any, Dict[str, Any]]]:
        """
        Compute value distributions (count / percentage / No. list) for selected columns.

        :param columns: List of column names to summarize.
        :return: Dictionary keyed by column name, with per-value statistics.
        """
        result: Dict[str, Dict[Any, Dict[str, Any]]] = {}
        total_rows = len(self.df)

        for col in columns:
            if col not in self.df.columns:
                self.logger.warning(
                    f"[WARN] Column '{col}' not found in data; skipping value distribution."
                )
                continue

            value_counts = self.df[col].value_counts(dropna=False)
            col_stats: Dict[Any, Dict[str, Any]] = {}

            for value, count in value_counts.items():
                pct = (count / total_rows * 100.0) if total_rows > 0 else 0.0
                no_list = self.df.loc[self.df[col] == value, self.NO_COL].tolist()

                col_stats[value] = {
                    "count": int(count),
                    "percentage": pct,
                    "no_list": no_list,
                }

            result[col] = col_stats

        return result

    def _build_summary_text(
        self,
        missing_stats: Dict[str, Dict[str, Any]],
        value_stats: Dict[str, Dict[Any, Dict[str, Any]]],
    ) -> str:
        """
        Build the plain-text summary report for quality assessment analysis.

        :param missing_stats: Column-wise missingness statistics.
        :param value_stats: Value distribution statistics for key fields.
        :return: Formatted report text.
        """
        lines: List[str] = []

        lines.append("=" * 70)
        lines.append("Quality Assessment Summary Report")
        lines.append("=" * 70)
        lines.append(f"\nTotal records (rows): {len(self.df)}\n")

        lines.append("1. Column-wise Missingness Overview")
        lines.append("-" * 70)

        for col, stats in missing_stats.items():
            line = (
                f"- {col}: missing {stats['missing_count']} / {len(self.df)} "
                f"({stats['missing_percentage']:.2f}%)"
            )
            if stats["nr_na_count"] > 0:
                line += f" | 'NR'/'NA' rows: {stats['nr_na_count']}"
            lines.append(line)
            if stats["nr_na_no_list"]:
                lines.append(f"    NR/NA No.: {stats['nr_na_no_list']}")
        lines.append("")

        lines.append("2. Value Distribution for Key Quality Fields")
        lines.append("-" * 70)

        for col in self.CORE_STATS_COLUMNS:
            lines.append(f"- {col}:")
            for value, stat in sorted(
                value_stats.get(col, {}).items(),
                key=lambda kv: (-kv[1]["count"], str(kv[0])),
            ):
                lines.append(
                    f"    {value!r}: count={stat['count']} "
                    f"({stat['percentage']:.2f}%) | No.: {stat['no_list']}"
                )
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _write_summary(self, text: str, output_path: Optional[str] = None) -> None:
        """
        Write the summary text to a TXT file.

        :param text: Report text to write.
        :param output_path: Optional override for the output path; if None,
                            self.summary_path is used.
        """
        if not output_path:
            output_path = self.summary_path
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(text, encoding="utf-8")
        self.logger.info(f"[INFO] Quality assessment summary report written to: {output_path}")

    def run(self) -> None:
        """
        Main execution entry point: perform quality assessment analysis and
        write the TXT report.

        :return: None
        """
        missing_stats = self._get_missing_stats()
        value_stats = self._get_value_stats(self.CORE_STATS_COLUMNS)
        summary_text = self._build_summary_text(missing_stats, value_stats)
        self._write_summary(summary_text)


def main() -> None:
    """
    Script entry point: run the quality assessment analysis and generate the
    TXT report.

    :return: None
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] quality_assessment_analysis script started.")

    analyzer = QualityAssessmentAnalyzer(logger=logger)
    analyzer.run()

    logger.info("[MAIN] quality_assessment_analysis script finished.")


if __name__ == "__main__":
    main()
