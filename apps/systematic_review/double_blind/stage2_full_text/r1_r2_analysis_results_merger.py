# -*- coding: utf-8 -*-
"""
r1_r2_analysis_results_merger.py

Merge Stage 2 (Full-text) R1 and R2 screening results on a shared key space:

    - "No."
    - "Title"
    - "Year"

Design
------
- Treat R1_analysis_results.xlsx as the base table
  (all non-decision columns are taken from R1).
- Attach only the Decision / Notes columns from R2_analysis_results.xlsx.
- Normalize key fields in both R1 / R2 before any comparison.
- Validate that R1 and R2 share an identical key set after normalization.
- Produce the following decision/notes fields:

      R1_Decision, R1_Notes  (from R1_analysis_results.xlsx)
      R2_Decision, R2_Notes  (from R2_analysis_results.xlsx)
      R3_Need                (derived flag for R3 adjudication)

R3_Need rules
-------------
- "Yes" if R1_Decision = R2_Decision = "unsure"
- "Yes" if R1_Decision != R2_Decision
- "No" otherwise

Before writing the final file, R1_Notes and R2_Notes are formatted as
pretty JSON (4-space indentation) where valid JSON strings are detected.

Final output
------------
The final result is saved as R1_R2_analysis_results.xlsx in the Stage 2 directory,
with columns ordered as:

    ['No.', 'Title', 'Year',
     'R1_Decision', 'R1_Notes',
     'R2_Decision', 'R2_Notes',
     'R3_Need', 'Remark']

The 'Remark' column is created as an empty string column if not present.

Author: Aiden Cao <zhinengmahua@gmail.com>
Date  : 2025-12-06
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from apps.systematic_review.utils.data_io import load_table, save_table
from apps.systematic_review.utils.exceptions import DataValidationError
from apps.systematic_review.utils.logger_manager import LoggerManager

# File names (relative to Stage 2 root)
R1_ANALYSIS_FILE = "R1_analysis_results.xlsx"
R2_ANALYSIS_FILE = "R2_analysis_results.xlsx"
OUTPUT_FILE = "R1_R2_analysis_results.xlsx"

# Key fields for alignment / consistency checks
KEY_FIELDS: List[str] = ["No.", "Title", "Year"]
KeyTuple = Tuple[str, ...]

# Final output column order (规范后的统一命名)
OUTPUT_COLUMNS: List[str] = [
    "No.",
    "Title",
    "Year",
    "R1_Decision",
    "R1_Notes",
    "R2_Decision",
    "R2_Notes",
    "R3_Need",
    "Remark",
]


def setup_logger(
    name: str = "r1r2_analysis_results_merger",
    verbose: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger instance.

    :param name: Logger name.
    :param verbose: Whether to enable DEBUG-level logs.
    :return: Configured logging.Logger instance.
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class R1R2AnalysisMerger:
    """
    Merge R1 / R2 analysis results and derive R3_Need on a common key space.

    Responsibilities
    ----------------
    - Resolve Stage 2 directory.
    - Load raw R1 / R2 analysis tables.
    - Normalize and validate key sets.
    - Prepare R1 base and R2 decision slices.
    - Merge R1 + R2 decisions and compute R3_Need.
    - Normalize R1_Notes / R2_Notes to pretty JSON where applicable.
    - Reorder and trim columns to the required final schema.
    - Save the final merged results.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the merger and resolve the Stage 2 directory.

        :param logger: Optional logger instance; if None, a default logger is created.
        :raises DataValidationError: If the Stage 2 directory does not exist.
        """
        self.logger = logger or setup_logger()

        project_root = Path(__file__).resolve().parents[4]
        self.stage_root = (
            project_root
            / "data"
            / "systematic_review"
            / "double_blind"
            / "stage2_full_text"
        )

        if not self.stage_root.is_dir():
            raise DataValidationError(
                f"Stage 2 directory does not exist: {self.stage_root}"
            )

        self.logger.info(f"[PATH] Stage 2 directory: {self.stage_root}")

    # -------------------------------------------------------------------------
    # Generic utilities
    # -------------------------------------------------------------------------

    def _load_file(self, file_path: Path) -> pd.DataFrame:
        """
        Load a table from disk and wrap low-level exceptions in DataValidationError.

        :param file_path: Path to the file.
        :return: Loaded DataFrame.
        :raises DataValidationError: If the file cannot be loaded.
        """
        try:
            return load_table(file_path, logger=self.logger)
        except Exception as exc:
            raise DataValidationError(f"Error loading file {file_path}: {exc}")

    @staticmethod
    def _require_columns(
        df: pd.DataFrame,
        filename: str,
        required: List[str],
    ) -> None:
        """
        Ensure that a DataFrame contains the required columns.

        :param df: DataFrame to check.
        :param filename: Name of the source file (for error messages).
        :param required: List of required column names.
        :raises DataValidationError: If any required columns are missing.
        """
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise DataValidationError(f"{filename} is missing required columns: {missing}")

    @staticmethod
    def _normalize_keys(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize key-related fields for robust comparison / merging.

        Standardization rules
        ---------------------
        - For KEY_FIELDS ("No.", "Title", "Year"):
            * cast to string
            * strip leading/trailing whitespace
        - If present:
          * "Title":
                cast to string, strip whitespace, lowercase
          * "Year":
                convert to numeric (invalid values become NaN) and store as Int64

        :param df: DataFrame to normalize.
        :return: Normalized copy of the input DataFrame.
        """
        df = df.copy()

        if "Title" in df.columns:
            df["Title"] = (df["Title"].astype(str).str.strip().str.lower())

        if "Year" in df.columns:
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")

        for col in KEY_FIELDS:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        return df

    @staticmethod
    def _build_key_tuples(df: pd.DataFrame) -> List[KeyTuple]:
        """
        Build a list of key tuples from KEY_FIELDS for each row.

        :param df: DataFrame containing KEY_FIELDS.
        :return: List of key tuples (one per row).
        """
        return [tuple(row) for row in df[KEY_FIELDS].to_numpy()]

    # -------------------------------------------------------------------------
    # Key consistency validation
    # -------------------------------------------------------------------------

    def _validate_key_consistency(
        self,
        df_r1_raw: pd.DataFrame,
        df_r2_raw: pd.DataFrame,
    ) -> None:
        """
        Validate that R1 and R2 analysis results have identical key sets (after normalization).

        Steps
        -----
        1. Normalize key fields in both R1 / R2 DataFrames.
        2. Ensure that all KEY_FIELDS exist in both tables.
        3. Build key sets and compare:
           - Report row counts and unique key counts.
           - If key sets differ, log samples and raise DataValidationError.

        :param df_r1_raw: Raw R1 analysis DataFrame.
        :param df_r2_raw: Raw R2 analysis DataFrame.
        :raises DataValidationError: If key sets are not exactly identical.
        """
        df_r1_norm = self._normalize_keys(df_r1_raw)
        df_r2_norm = self._normalize_keys(df_r2_raw)

        for df, name in (
            (df_r1_norm, R1_ANALYSIS_FILE),
            (df_r2_norm, R2_ANALYSIS_FILE),
        ):
            missing = [c for c in KEY_FIELDS if c not in df.columns]
            if missing:
                raise DataValidationError(f"{name} is missing key columns: {missing}")

        keys_r1 = set(self._build_key_tuples(df_r1_norm))
        keys_r2 = set(self._build_key_tuples(df_r2_norm))

        self.logger.info("[KEYS] R1/R2 key consistency check")
        self.logger.info(f"  R1: rows={len(df_r1_raw)}, unique keys={len(keys_r1)}")
        self.logger.info(f"  R2: rows={len(df_r2_raw)}, unique keys={len(keys_r2)}")

        only_in_r1 = keys_r1 - keys_r2
        only_in_r2 = keys_r2 - keys_r1

        if only_in_r1 or only_in_r2:
            self.logger.error(
                f"[KEYS] Key sets differ: only_in_R1={len(only_in_r1)}, "
                f"only_in_R2={len(only_in_r2)}"
            )
            if only_in_r1:
                sample_r1 = list(only_in_r1)[:5]
                self.logger.error(f"  Sample keys only in R1 (up to 5): {sample_r1}")
            if only_in_r2:
                sample_r2 = list(only_in_r2)[:5]
                self.logger.error(f"  Sample keys only in R2 (up to 5): {sample_r2}")
            raise DataValidationError(
                "R1 and R2 analysis results do not share identical key sets."
            )

        self.logger.info(
            "[KEYS] R1 and R2 have identical key sets (after normalization)."
        )

    # -------------------------------------------------------------------------
    # Preparation of R1 base and R2 decision slices
    # -------------------------------------------------------------------------

    def _prepare_r1_base(self, df_r1_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare the R1 base DataFrame from the raw R1 analysis results.

        This method:
        - Verifies presence of KEY_FIELDS + ['Decision', 'Notes'].
        - Renames 'Decision' → 'R1_Decision', 'Notes' → 'R1_Notes'.

        :param df_r1_raw: Raw R1 analysis DataFrame.
        :return: Prepared R1 base DataFrame.
        :raises DataValidationError: If required columns are missing.
        """
        self._require_columns(
            df_r1_raw,
            R1_ANALYSIS_FILE,
            KEY_FIELDS + ["Decision", "Notes"],
        )

        df_r1 = df_r1_raw.copy()
        df_r1.rename(
            columns={"Decision": "R1_Decision", "Notes": "R1_Notes"},
            inplace=True,
        )

        self.logger.info(
            f"[R1] Prepared base table from {R1_ANALYSIS_FILE} with {len(df_r1)} rows"
        )
        return df_r1

    def _prepare_r2_decisions(self, df_r2_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare the R2 decision slice from the raw R2 analysis results.

        This method:
        - Verifies presence of KEY_FIELDS + ['Decision', 'Notes'].
        - Returns a slim DataFrame with KEY_FIELDS + ['R2_Decision', 'R2_Notes'].

        :param df_r2_raw: Raw R2 analysis DataFrame.
        :return: R2 decision/notes DataFrame.
        :raises DataValidationError: If required columns are missing.
        """
        self._require_columns(
            df_r2_raw,
            R2_ANALYSIS_FILE,
            KEY_FIELDS + ["Decision", "Notes"],
        )

        df_r2 = df_r2_raw.copy()
        df_r2 = df_r2[KEY_FIELDS + ["Decision", "Notes"]]
        df_r2.rename(
            columns={"Decision": "R2_Decision", "Notes": "R2_Notes"},
            inplace=True,
        )

        self.logger.info(
            f"[R2] Prepared decision slice from {R2_ANALYSIS_FILE} with {len(df_r2)} rows"
        )
        return df_r2

    # -------------------------------------------------------------------------
    # Merge + R3_Need computation
    # -------------------------------------------------------------------------

    def _merge_r1_r2(self, df_r1: pd.DataFrame, df_r2: pd.DataFrame) -> pd.DataFrame:
        """
        Merge the prepared R1 base with prepared R2 decisions on KEY_FIELDS.

        R1 is used as the left/base DataFrame. The result includes:
        - All columns from R1 (with R1_Decision / R1_Notes).
        - R2_Decision / R2_Notes appended from R2 where keys match.

        :param df_r1: Prepared R1 base DataFrame.
        :param df_r2: Prepared R2 decisions DataFrame.
        :return: Merged DataFrame.
        """
        merged = pd.merge(
            df_r1,
            df_r2,
            on=KEY_FIELDS,
            how="left",
        )

        if len(merged) != len(df_r1):
            self.logger.warning(
                "[MERGE] Row count changed after merging R2 "
                f"(R1={len(df_r1)}, merged={len(merged)}). "
                "Check for duplicate or missing keys in R2."
            )
        else:
            self.logger.info(
                f"[MERGE] R1 + R2 merged with {len(merged)} rows (row count unchanged)."
            )

        return merged

    def _set_r3_need(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute the R3_Need flag based on R1_Decision / R2_Decision.

        Rules
        -----
        - Default 'R3_Need' = "No".
        - Set to "Yes" if:
          * R1_Decision == R2_Decision == "unsure" (case-insensitive), OR
          * R1_Decision != R2_Decision (case-insensitive).

        Notes
        -----
        - Comparisons are done on normalized lowercase copies of the decision
          columns, but the original values are preserved in the DataFrame.

        :param df: DataFrame with R1_Decision and R2_Decision columns.
        :return: DataFrame with R3_Need column added.
        :raises DataValidationError: If decision columns are missing.
        """
        df = df.copy()

        for col in ("R1_Decision", "R2_Decision"):
            if col not in df.columns:
                raise DataValidationError(
                    f"Expected column '{col}' is missing for R3_Need computation."
                )

        # Normalize decisions on temporary series to avoid mutating original text
        dec1 = df["R1_Decision"].astype(str).str.strip().str.lower()
        dec2 = df["R2_Decision"].astype(str).str.strip().str.lower()

        df["R3_Need"] = "No"

        unsure_both = (dec1 == "unsure") & (dec2 == "unsure")
        diff_decision = dec1 != dec2

        df.loc[unsure_both | diff_decision, "R3_Need"] = "Yes"

        self._log_r3_need(df)
        return df

    def _log_r3_need(self, df: pd.DataFrame) -> None:
        """
        Log summary statistics for the R3_Need column.

        :param df: DataFrame with the 'R3_Need' column.
        :return: None
        """
        counts = df["R3_Need"].value_counts(dropna=False)
        self.logger.info(f"[INFO] 'R3_Need' value counts:\n{counts}")

        yes_rows = df[df["R3_Need"] == "Yes"]
        self.logger.info(
            "[INFO] 'R3_Need' = 'Yes' for the following No. values:\n"
            f"{yes_rows['No.'].tolist()}"
        )

    # -------------------------------------------------------------------------
    # Notes JSON formatting
    # -------------------------------------------------------------------------

    @staticmethod
    def _format_notes_cell(val: object) -> str:
        """
        Format a single Notes cell as pretty JSON (4-space indentation) if possible.

        Rules
        -----
        - If val is None or NaN → return empty string.
        - If val is a str:
            * strip it; if empty → return empty string.
            * try json.loads; on success → json.dumps(..., indent=4, ensure_ascii=False).
            * on failure → return original string (unchanged).
        - For non-str (e.g., dict/list):
            * try json.dumps(..., indent=4, ensure_ascii=False).
            * on failure → cast to str and return.

        :param val: Original Notes cell value.
        :return: Formatted string.
        """
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""

        if isinstance(val, str):
            text = val.strip()
            if not text:
                return ""
            try:
                parsed = json.loads(text)
                return json.dumps(parsed, ensure_ascii=False, indent=4)
            except Exception:
                # Not valid JSON: return original string
                return val

        # Non-str: try to serialize as JSON
        try:
            return json.dumps(val, ensure_ascii=False, indent=4)
        except Exception:
            return str(val)

    def _normalize_notes_columns(
        self,
        df: pd.DataFrame,
        note_columns: List[str],
    ) -> pd.DataFrame:
        """
        Normalize given Notes columns to pretty JSON format where applicable.

        :param df: DataFrame containing the Notes columns.
        :param note_columns: Column names to format (e.g., ['R1_Notes', 'R2_Notes']).
        :return: DataFrame with Notes columns formatted.
        """
        df = df.copy()
        for col in note_columns:
            if col in df.columns:
                df[col] = df[col].apply(self._format_notes_cell)
            else:
                # Soft warning only; schema differences can be handled upstream.
                # 这里仅记录日志，不中断流程。
                logging.getLogger(__name__).warning(
                    f"[WARN] Notes column '{col}' not found; JSON formatting skipped."
                )
        return df

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    def _reorder_and_trim_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reorder and trim columns to match the required OUTPUT_COLUMNS schema.

        Behavior
        --------
        - Ensures that all columns in OUTPUT_COLUMNS exist:
          * if 'Remark' is missing, an empty string column is created.
          * for other missing columns, raise DataValidationError.
        - Drops any extra columns not listed in OUTPUT_COLUMNS.
        - Reorders columns to exactly match OUTPUT_COLUMNS.

        :param df: Merged DataFrame with decision and notes columns.
        :return: DataFrame containing only OUTPUT_COLUMNS in the desired order.
        :raises DataValidationError: If any non-optional output column is missing.
        """
        df = df.copy()

        for col in OUTPUT_COLUMNS:
            if col in df.columns:
                continue
            if col == "Remark":
                df[col] = ""
            else:
                raise DataValidationError(
                    f"Expected output column '{col}' is missing in merged results."
                )

        df = df[OUTPUT_COLUMNS]
        return df

    def _save_results(self, df: pd.DataFrame) -> None:
        """
        Save the final merged DataFrame to the Stage 2 directory.

        The DataFrame is first reordered and trimmed to OUTPUT_COLUMNS.

        :param df: DataFrame to save.
        :return: None
        :raises DataValidationError: If the file cannot be saved.
        """
        try:
            output_path = self.stage_root / OUTPUT_FILE
            final_df = self._reorder_and_trim_columns(df)
            save_table(final_df, output_path, logger=self.logger)
            self.logger.info(
                f"[INFO] Merged R1/R2 analysis results saved to {output_path}"
            )
        except Exception as exc:
            raise DataValidationError(
                f"Error saving merged results to {OUTPUT_FILE}: {exc}"
            )

    # -------------------------------------------------------------------------
    # Orchestration
    # -------------------------------------------------------------------------

    def run(self) -> None:
        """
        Run the full R1/R2 analysis merge process.

        Pipeline
        --------
        1. Load raw R1 and R2 analysis tables.
        2. Normalize keys and validate that R1 / R2 share identical key sets.
        3. Prepare R1 base and R2 decision slices from the raw tables.
        4. Merge them on KEY_FIELDS.
        5. Compute R3_Need based on R1_Decision / R2_Decision.
        6. Normalize R1_Notes / R2_Notes as pretty JSON where applicable.
        7. Reorder/trim columns and save the final merged results.

        :return: None
        :raises DataValidationError: If any validation or I/O error occurs.
        """
        # 1. Load raw tables
        r1_path = self.stage_root / R1_ANALYSIS_FILE
        r2_path = self.stage_root / R2_ANALYSIS_FILE

        df_r1_raw = self._load_file(r1_path)
        df_r2_raw = self._load_file(r2_path)

        # 2. Validate key consistency after normalization
        self._validate_key_consistency(df_r1_raw, df_r2_raw)

        # 3. Prepare R1 base and R2 decisions
        df_r1 = self._prepare_r1_base(df_r1_raw)
        df_r2 = self._prepare_r2_decisions(df_r2_raw)

        # 4. Merge and compute R3_Need
        merged_df = self._merge_r1_r2(df_r1, df_r2)
        merged_df = self._set_r3_need(merged_df)

        # 5 / 6. Normalize R1_Notes / R2_Notes to pretty JSON (4-space indentation)
        merged_df = self._normalize_notes_columns(
            merged_df,
            ["R1_Notes", "R2_Notes"],
        )

        # 7. Save with required column order
        self._save_results(merged_df)


def main() -> None:
    """
    Script entry point for the R1/R2 analysis results merge process.

    :return: None
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] Starting R1/R2 analysis results merge process")

    merger = R1R2AnalysisMerger(logger=logger)
    merger.run()

    logger.info("[MAIN] R1/R2 analysis results merge process completed")


if __name__ == "__main__":
    main()