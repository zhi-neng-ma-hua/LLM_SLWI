# -*- coding: utf-8 -*-
"""
final_included_literature_filter.py

Purpose
-------
Automatically identify and export the “final included” studies based on
the results of the quality assessment.

Directory conventions
---------------------
- Quality assessment results table:
    project_root / data / systematic_review / quality_assessment / quality_assessment_table.xlsx
- Data extraction master table:
    project_root / data / systematic_review / data_extraction / data_extraction_table.xlsx
- Final included literature table (output of this script):
    project_root / data / systematic_review / final_included_literature.xlsx

Core functionality
------------------
1. From quality_assessment_table.xlsx, select rows with quality_category = "High"
   and collect the corresponding values in the No. column.
2. In data_extraction_table.xlsx, filter rows by No. to retain the full records
   of these high-quality studies.
3. Export the filtered results to final_included_literature.xlsx as the final
   included literature list.

Author: Aiden Cao <zhinengmahua@gmail.com>
Date: 2025-07-13
"""

import logging
from pathlib import Path
from typing import Optional, List, Any

import pandas as pd

from apps.systematic_review.utils.logger_manager import LoggerManager


def setup_logger(
    name: str = "final_included_literature_filter",
    verbose: bool = True,
) -> logging.Logger:
    """
    Unified entry point for obtaining a configured logger.

    :param name: Logger name.
    :param verbose: Whether to enable verbose DEBUG logging.
    :return: logging.Logger instance.
    :raises Exception: Any exception will be raised by LoggerManager.setup_logger.
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class FinalIncludedLiteratureFilter:
    """
    Controller for filtering the final included literature based on
    the quality assessment and data extraction tables, and exporting
    the resulting subset.
    """

    QUALITY_ASSESSMENT_FILE = "quality_assessment_table.xlsx"
    DATA_EXTRACTION_FILE = "data_extraction_table.xlsx"
    FINAL_OUTPUT_FILE = "final_included_literature.xlsx"

    QA_SHEET_NAME = "Quality_Assessment_Data"
    QA_NO_COL = "No."
    QA_QUALITY_COL = "quality_category"
    QA_TITLE_COL = "Title"

    DE_NO_COL = "No."

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the controller, resolve file paths, and load data.

        :param logger: Logger instance; if None, a default logger is created.
        :raises FileNotFoundError: If any required input file is missing.
        :raises Exception: If reading Excel files fails.
        """
        self.logger = logger or setup_logger()
        self._init_paths()
        self.df_quality = self._load_quality_assessment()
        self.df_extraction = self._load_data_extraction()

    def _init_paths(self) -> None:
        """
        Initialize and validate paths for the quality assessment table,
        data extraction table, and output file.

        :return: None
        :raises FileNotFoundError: If the quality assessment or data extraction
                                   file does not exist.
        """
        project_root = Path(__file__).resolve().parents[2]
        qa_dir = project_root / "data" / "systematic_review" / "quality_assessment"
        de_dir = project_root / "data" / "systematic_review" / "data_extraction"
        out_dir = project_root / "data" / "systematic_review"

        self.qa_path = qa_dir / self.QUALITY_ASSESSMENT_FILE
        self.de_path = de_dir / self.DATA_EXTRACTION_FILE
        self.output_path = out_dir / self.FINAL_OUTPUT_FILE

        missing_paths = [p for p in (self.qa_path, self.de_path) if not p.is_file()]
        if missing_paths:
            for p in missing_paths:
                self.logger.error(f"[ERROR] Input file does not exist: {p}")
            raise FileNotFoundError(
                f"The following input files were not found: {[str(p) for p in missing_paths]}"
            )

        self.logger.info(
            "[PATH] Quality assessment table: %s\n"
            "[PATH] Data extraction table: %s\n"
            "[PATH] Output file           : %s",
            self.qa_path,
            self.de_path,
            self.output_path,
        )

    def _load_quality_assessment(self) -> pd.DataFrame:
        """
        Load the quality assessment results table
        (quality_assessment_table.xlsx / Sheet=Quality_Assessment_Data).

        :return: DataFrame containing quality assessment results.
        :raises Exception: If reading the Excel file fails or required
                          columns are missing.
        """
        try:
            df = pd.read_excel(self.qa_path, sheet_name=self.QA_SHEET_NAME)
        except Exception as exc:
            self.logger.error(
                "[ERROR] Failed to read quality assessment table: %s | Error: %s",
                self.qa_path,
                exc,
            )
            raise

        missing_cols = [c for c in (self.QA_NO_COL, self.QA_QUALITY_COL) if c not in df.columns]
        if missing_cols:
            self.logger.error(
                "[ERROR] Quality assessment table is missing required columns: %s",
                missing_cols,
            )
            raise KeyError(f"Quality assessment table missing required columns: {missing_cols}")

        self.logger.info(
            "[INFO] Quality assessment table loaded: rows=%d, columns=%d",
            len(df),
            len(df.columns),
        )
        return df

    def _load_data_extraction(self) -> pd.DataFrame:
        """
        Load the data extraction master table (data_extraction_table.xlsx).

        :return: DataFrame containing data extraction results.
        :raises Exception: If reading the Excel file fails or required
                          columns are missing.
        """
        try:
            df = pd.read_excel(self.de_path)
        except Exception as exc:
            self.logger.error(
                "[ERROR] Failed to read data extraction table: %s | Error: %s",
                self.de_path,
                exc,
            )
            raise

        if self.DE_NO_COL not in df.columns:
            self.logger.error(
                "[ERROR] Data extraction table is missing required column: %s",
                self.DE_NO_COL,
            )
            raise KeyError(f"Data extraction table missing required column: {self.DE_NO_COL}")

        self.logger.info(
            "[INFO] Data extraction table loaded: rows=%d, columns=%d",
            len(df),
            len(df.columns),
        )
        return df

    def _normalize_no_series(self, series: pd.Series) -> pd.Series:
        """
        Normalize the No. column by stripping whitespace and converting
        values to numeric where possible, to improve matching robustness.

        :param series: Original No. column.
        :return: Normalized No. column as numeric (where possible).
        """
        s = series.astype(str).str.strip()
        return pd.to_numeric(s, errors="coerce")

    def _get_high_quality_no_list(self) -> List[Any]:
        """
        From the quality assessment table, select rows where
        quality_category = "High" and return the corresponding No. values.

        :return: List of No. values meeting the selection criterion.
        """
        qa = self.df_quality.copy()

        quality = qa[self.QA_QUALITY_COL].astype(str).str.strip().str.lower()
        mask_high = quality == "high"

        high_df = qa.loc[mask_high]
        if high_df.empty:
            self.logger.warning(
                "[WARN] No records with quality_category = 'High' were found "
                "in the quality assessment table."
            )
            return []

        no_series = self._normalize_no_series(high_df[self.QA_NO_COL])
        no_list = no_series.dropna().tolist()

        self.logger.info(
            "[INFO] Selected records with quality_category = 'High': %d rows, "
            "unique No. values: %d",
            len(high_df),
            len(set(no_list)),
        )
        return no_list

    def _filter_extraction_by_no(self, no_list: List[Any]) -> pd.DataFrame:
        """
        Filter the data extraction table by a list of No. values.

        :param no_list: List of No. values to retain.
        :return: Filtered DataFrame containing only selected records.
        """
        df = self.df_extraction.copy()
        df[self.DE_NO_COL] = self._normalize_no_series(df[self.DE_NO_COL])

        mask = df[self.DE_NO_COL].isin(no_list)
        filtered = df.loc[mask].copy()

        self.logger.info(
            "[INFO] Filtered data extraction table using 'High' quality No. values: "
            "retained rows=%d, proportion=%.2f%%",
            len(filtered),
            (len(filtered) / len(df) * 100.0) if len(df) > 0 else 0.0,
        )

        return filtered

    def _save_filtered(self, df: pd.DataFrame) -> None:
        """
        Export the final included literature DataFrame to an Excel file.

        :param df: Final included literature DataFrame.
        :return: None
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Insert "Title" column at position 1
            df.insert(1, self.QA_TITLE_COL, df.pop(self.QA_TITLE_COL))
            df.to_excel(self.output_path, index=False)
            self.logger.info(
                "[EXPORT] Final included literature table written to: %s | rows=%d | columns=%d",
                self.output_path,
                len(df),
                len(df.columns),
            )
        except Exception as exc:
            self.logger.error(
                "[ERROR] Failed to write Excel file: %s | Error: %s",
                self.output_path,
                exc,
            )
            raise

    def run(self) -> None:
        """
        Main execution entry point: run the full pipeline from quality
        assessment filtering to exporting the final included literature list.

        :return: None
        """
        self.logger.info("[MAIN] Starting final included literature filtering pipeline.")

        high_no_list = self._get_high_quality_no_list()
        final_df = self._filter_extraction_by_no(high_no_list)

        # Add the Title column from the quality assessment table to the final
        # data table, and ensure it will be placed as the second column.
        final_df[self.QA_TITLE_COL] = self.df_quality.loc[
            self.df_quality[self.QA_NO_COL].isin(high_no_list), self.QA_TITLE_COL
        ].values

        self._save_filtered(final_df)

        self.logger.info("[MAIN] Final included literature filtering pipeline completed.")


def main() -> None:
    """
    Script entry point: execute the final included literature filtering
    pipeline and export the results.

    :return: None
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] final_included_literature_filter script started.")

    processor = FinalIncludedLiteratureFilter(logger=logger)
    processor.run()

    logger.info("[MAIN] final_included_literature_filter script finished.")


if __name__ == "__main__":
    main()