# -*- coding: utf-8 -*-
"""
merge_double_blind_batches.py

Purpose:
    1. Read batch result files under the double-blind result directories
       matching the pattern "Rx_analysis_batch_XXX.csv":
           data/systematic_review/double_blind/stage1_title_abstract/R1/
           data/systematic_review/double_blind/stage1_title_abstract/R2/
    2. Merge batches in ascending order of batch index (preserving row order
       within each file) and normalize the Notes column into pretty-printed
       JSON with indentation.
    3. Add a leading "No." column to the merged result (auto-increment from 1).
    4. Write the merged results to single CSV files:
           data/systematic_review/double_blind/stage1_title_abstract/R1/R1_analysis_results.csv
           data/systematic_review/double_blind/stage1_title_abstract/R2/R2_analysis_results.csv

Author: SmartMahua <zhinengmahua@gmail.com>
Date: 2025-05-22
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

from apps.systematic_review.utils.exceptions import DataValidationError
from apps.systematic_review.utils.logger_manager import LoggerManager


def get_logger(name: str = "double_blind_batch_merger", verbose: bool = True) -> logging.Logger:
    """
    Get a configured logger instance.

    :param name: Logger name.
    :param verbose: If True, enable DEBUG-level logging.
    :return: Configured logging.Logger instance.
    """
    try:
        return LoggerManager.setup_logger(
            logger_name=name,
            module_name=__name__,
            verbose=verbose,
        )
    except Exception as ex:
        raise RuntimeError(f"Logger initialization failed: {ex}") from ex


class DoubleBlindBatchMerger:
    """Merger for double-blind batch CSV result files."""

    def __init__(
        self,
        round_label: str,
        batch_dir: Path,
        output_csv_path: Path,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize a double-blind batch result merger.

        :param round_label: Round label (e.g. "R1" or "R2").
        :param batch_dir: Directory containing batch CSV result files.
        :param output_csv_path: Output CSV path for the merged results.
        :param logger: Optional logger instance; if None, a default logger is created.
        :return: None
        """
        if not isinstance(batch_dir, Path):
            raise DataValidationError("batch_dir must be of type pathlib.Path")
        if not batch_dir.exists() or not batch_dir.is_dir():
            raise DataValidationError(f"Batch directory does not exist or is not a directory: {batch_dir}")

        self.round_label = round_label
        self.batch_dir = batch_dir
        self.output_csv_path = output_csv_path
        self.logger = logger or get_logger("double_blind_batch_merger", verbose=True)

    def _scan_batch_files(self) -> List[Path]:
        """
        Scan the batch directory for all CSV files that match the naming pattern.

        :return: List of batch file paths sorted in ascending order by file name.
        """
        # Example: R1_analysis_batch_000.csv, R1_analysis_batch_001.csv
        pattern = f"{self.round_label}_analysis_batch_*.csv"
        batch_files = sorted(self.batch_dir.glob(pattern))

        if not batch_files:
            self.logger.warning(
                f"[Scan] No batch files found in directory {self.batch_dir} (pattern: {pattern})."
            )
        else:
            self.logger.info(
                f"[Scan] Round {self.round_label} found {len(batch_files)} batch files in {self.batch_dir}."
            )
            for path in batch_files:
                self.logger.debug(f"  - {path.name}")
        return batch_files

    @staticmethod
    def _normalize_notes_value(val: Any) -> str:
        """
        Normalize a Notes cell value to a pretty-printed JSON string.

        :param val: Original cell value.
        :return: Normalized string representation.
        """
        # Empty value
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""

        # dict / list: format directly
        if isinstance(val, (dict, list)):
            return json.dumps(val, ensure_ascii=False, indent=4)

        # String: try to parse as JSON
        if isinstance(val, str):
            stripped = val.strip()
            if not stripped:
                return ""
            try:
                obj = json.loads(stripped)
                return json.dumps(obj, ensure_ascii=False, indent=4)
            except Exception:
                # Invalid JSON, keep original content unchanged
                return val

        # Fallback: convert other types to string
        return str(val)

    def _merge_batches(self, batch_csv_paths: List[Path]) -> None:
        """
        Merge all batch CSV files into a single result file.

        :param batch_csv_paths: List of batch CSV file paths.
        :return: None
        """
        if not batch_csv_paths:
            self.logger.warning(
                f"[Merge skipped] No batch result files found for round {self.round_label} "
                f"in directory {self.batch_dir}. Aborting merge."
            )
            return

        data_frames: List[pd.DataFrame] = []
        total_rows = 0

        for path in batch_csv_paths:
            try:
                df = pd.read_csv(path, encoding="utf-8-sig")

                # Normalize Notes column to JSON if present
                if "Notes" in df.columns:
                    df["Notes"] = df["Notes"].apply(self._normalize_notes_value)

                rows = len(df)
                data_frames.append(df)
                total_rows += rows
                self.logger.info(f"[Batch read] {path.name} rows={rows}")
            except Exception as e:
                self.logger.error(f"[Batch read failed] {path}: {e}", exc_info=True)

        if not data_frames:
            self.logger.error(
                f"[Merge aborted] All batch files for round {self.round_label} failed to read. No usable data."
            )
            return

        # Concatenate in ascending file-name order, preserving row order within each file
        total_df = pd.concat(data_frames, ignore_index=True)
        self.logger.info(
            f"[Merge summary] Round {self.round_label} total rows before merge={total_rows}, "
            f"after merge={len(total_df)}"
        )

        # Add an auto-increment "No." column at the leftmost position (starting from 1)
        try:
            if "No." in total_df.columns:
                total_df = total_df.drop(columns=["No."])
            total_df.insert(0, "No.", range(1, len(total_df) + 1))
            self.logger.info(
                f"[Indexing] Round {self.round_label} added No. column with range 1~{len(total_df)}"
            )
        except Exception as e:
            self.logger.error(
                f"[Indexing failed] Round {self.round_label} encountered an error while generating No. column: {e}",
                exc_info=True,
            )
            # Do not interrupt subsequent write; just log the error

        try:
            self.output_csv_path.parent.mkdir(parents=True, exist_ok=True)
            total_df.to_csv(self.output_csv_path, index=False, encoding="utf-8-sig")
            self.logger.info(
                f"[Merge completed] Round {self.round_label} written to: {self.output_csv_path} | "
                f"total entries: {len(total_df)}"
            )
        except Exception as e:
            self.logger.critical(
                f"[Write failed] Round {self.round_label} could not write to {self.output_csv_path}: {e}",
                exc_info=True,
            )
            raise

    def run(self) -> None:
        """
        Execute the merge pipeline for a single round directory.

        :return: None
        """
        self.logger.info(
            f"[Start] Round {self.round_label} double-blind batch merge task. Directory={self.batch_dir}"
        )
        batch_files = self._scan_batch_files()
        self._merge_batches(batch_files)


def main() -> None:
    """
    Script entry point: merge double-blind batch results for R1 and R2.

    :return: None
    """
    try:
        # This script is located under apps/systematic_review/double_blind/
        project_root = Path(__file__).resolve().parents[3]
    except Exception as e:
        print(f"[ERROR] Failed to infer project root: {e}")
        sys.exit(1)

    base_dir = project_root / "data" / "systematic_review" / "double_blind" / "stage1_title_abstract"

    # R1 / R2 directories and output file paths
    r1_dir = base_dir / "R1"
    r2_dir = base_dir / "R2"
    r1_output_csv = r1_dir / "R1_analysis_results.csv"
    r2_output_csv = r2_dir / "R2_analysis_results.csv"

    logger = get_logger(verbose=True)

    # Merge R1 batch results
    try:
        r1_merger = DoubleBlindBatchMerger("R1", r1_dir, r1_output_csv, logger=logger)
        r1_merger.run()
    except Exception as e:
        logger.critical(f"[R1 merge error] {e}", exc_info=True)
        # Do not exit immediately; continue processing R2

    # Merge R2 batch results
    try:
        r2_merger = DoubleBlindBatchMerger("R2", r2_dir, r2_output_csv, logger=logger)
        r2_merger.run()
    except Exception as e:
        logger.critical(f"[R2 merge error] {e}", exc_info=True)

    logger.info("[Main process completed] Double-blind batch merge task finished.")
    sys.exit(0)


if __name__ == "__main__":
    main()