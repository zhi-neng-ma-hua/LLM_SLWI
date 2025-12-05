# -*- coding: utf-8 -*-
"""
quality_assessment_texts_merger.py

Purpose
-------
Merge all JSON-style .txt quality assessment files in
data/systematic_review/quality_assessment/quality_assessment_texts
into a single Excel table:

    data/systematic_review/quality_assessment/quality_assessment_table.xlsx

Core Functionality
------------------
1. Scan all .txt files in the specified directory.
2. Parse each .txt file into a JSON object.
3. Flatten nested JSON (if present) into a single "wide row" record.
4. Vertically concatenate all records into a DataFrame.
5. Add a "no" column whose value is the .txt filename stem (without extension).
6. When flattening keys, automatically strip any Chinese annotation, keeping
   only the English key.
7. Before writing, convert the "no" column and all score columns to integer
   type (Int64).
8. Before writing, sort rows in ascending order by "no" (integer-based).
9. Summarize column-wise missingness (empty string / whitespace-only / NaN)
   and log the results.
10. Reorder columns according to a predefined logical order
    (metadata → total score → item scores and notes → others).
11. Export the final result as quality_assessment_table.xlsx for subsequent
    quality assessment analysis and synthesis.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from apps.systematic_review.utils.logger_manager import LoggerManager


def setup_logger(
    name: str = "quality_assessment_texts_merger",
    verbose: bool = True,
) -> logging.Logger:
    """
    Standard unified logger factory.

    :param name: Logger name.
    :param verbose: Whether to enable detailed DEBUG logging.
    :return: logging.Logger instance.
    :raises Exception: Any exception will be raised by LoggerManager.setup_logger.
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class QualityAssessmentTextsMerger:
    """
    Controller for merging JSON-style .txt quality assessment files.
    """

    INPUT_SUBDIR = "quality_assessment_texts"
    OUTPUT_FILENAME = "quality_assessment_table.xlsx"

    # Recommended column order (existing columns will be arranged in this order;
    # remaining columns are appended at the end in alphabetical order).
    PREFERRED_COLUMN_ORDER: List[str] = [
        # 1) Core metadata and key identifiers
        "no",
        "study_id",
        "first_author_year",
        "year",
        "title_short",
        "country_region",
        "llm_type_brief",
        "design_note_llm_specific",
        # 2) Overall quality and synthesis decisions
        "total_quality_score",
        "quality_category",
        "key_quality_concerns",
        "include_in_main_synthesis",
        "include_in_meta_analysis",
        # 3) Item-level quality scores (score → notes)
        "q1_research_aims_clarity_score",
        "q1_research_aims_clarity_notes",
        "q2_participant_info_score",
        "q2_participant_info_notes",
        "q3_sampling_and_power_score",
        "q3_sampling_and_power_notes",
        "q4_group_allocation_and_bias_score",
        "q4_group_allocation_and_bias_notes",
        "q5_longitudinal_design_score",
        "q5_longitudinal_design_notes",
        "q6_measurement_reliability_validity_score",
        "q6_measurement_reliability_validity_notes",
        "q7_intervention_procedure_and_duration_score",
        "q7_intervention_procedure_and_duration_notes",
        "q8_statistical_method_appropriateness_score",
        "q8_statistical_method_appropriateness_notes",
        "q9_assumption_and_effect_size_score",
        "q9_assumption_and_effect_size_notes",
        "q10_outliers_and_interpretation_score",
        "q10_outliers_and_interpretation_notes",
        # 4) Other auxiliary metadata
        "no_raw",
    ]

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the merger: resolve paths and configure the logger.

        :param logger: Logger instance; if None, the default logger is used.
        :raises FileNotFoundError: If the input directory does not exist.
        """
        self.logger = logger or setup_logger()
        self._init_paths()

    def _init_paths(self) -> None:
        """
        Initialize and validate input/output paths.

        :return: None
        :raises FileNotFoundError: If the TXT input directory does not exist.
        """
        # Current file:
        # apps/systematic_review/quality_assessment/quality_assessment_texts_merger.py
        # parents[0] = quality_assessment, parents[1] = systematic_review,
        # parents[2] = apps, parents[3] = project root
        project_root = Path(__file__).resolve().parents[3]
        base_data_dir = project_root / "data" / "systematic_review" / "quality_assessment"

        self.input_dir = base_data_dir / self.INPUT_SUBDIR
        self.output_path = base_data_dir / self.OUTPUT_FILENAME

        if not self.input_dir.is_dir():
            raise FileNotFoundError(f"TXT input directory does not exist: {self.input_dir}")

        self.logger.info(
            f"[PATH] TXT input directory: {self.input_dir} | "
            f"Merged output file: {self.output_path}"
        )

    @staticmethod
    def _clean_field_key(raw_key: str) -> str:
        """
        Clean the original field name, keeping only the English portion
        (strip Chinese annotation and parentheses).

        :param raw_key: Raw field key (may contain both English and Chinese).
        :return: Cleaned field name (English-only part).
        """
        return raw_key.split(" (", 1)[0].strip()

    @staticmethod
    def _flatten_json(
        obj: Dict[str, Any],
        no_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flatten a JSON object (optionally with one level of nesting) into a
        single-row "wide table" dictionary.

        :param obj: JSON object corresponding to a single quality assessment record.
        :param no_value: Value for the "no" column (typically the TXT filename stem).
        :return: Flattened single-row dictionary.
        """
        record: Dict[str, Any] = {}

        # Use filename stem as the "no" column to facilitate indexing and sorting.
        if no_value is not None:
            record["no"] = no_value

        for section, fields in obj.items():
            # Top-level non-dict fields are treated as standalone columns.
            if not isinstance(fields, dict):
                clean_key = QualityAssessmentTextsMerger._clean_field_key(str(section))
                # If the JSON object itself contains a "no" field, prioritize the
                # filename-based "no" and optionally keep the original value as "no_raw".
                if clean_key == "no" and no_value is not None:
                    record.setdefault("no_raw", fields)
                else:
                    record[clean_key] = fields
                continue

            # For nested structures, use "Section.field" as the flattened column name.
            for raw_key, value in fields.items():
                clean_key = QualityAssessmentTextsMerger._clean_field_key(str(raw_key))
                col_name = f"{section}.{clean_key}"
                record[col_name] = value

        return record

    def _load_single_txt(self, path: Path) -> Optional[Dict[str, Any]]:
        """
        Read and parse a single .txt file as a JSON object.

        :param path: Path to the .txt file.
        :return: Parsed JSON dictionary if successful; None for empty/invalid files.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            self.logger.error(f"[ERROR] Unable to read file: {path} | Error: {exc}")
            return None

        # Empty or whitespace-only file: log a warning and skip.
        if not text.strip():
            self.logger.warning(f"[WARN] File is empty or whitespace-only, skipped: {path}")
            return None

        try:
            data = json.loads(text)
            return data
        except Exception as exc:
            self.logger.error(f"[ERROR] Failed to parse JSON from file: {path} | Error: {exc}")
            return None

    def _collect_records(self) -> List[Dict[str, Any]]:
        """
        Scan all .txt files and collect flattened records.

        :return: List of flattened records, one per .txt file.
        """
        records: List[Dict[str, Any]] = []
        txt_files = sorted(self.input_dir.glob("*.txt"))

        if not txt_files:
            self.logger.warning(f"[WARN] No .txt files found in directory: {self.input_dir}")
            return records

        self.logger.info(f"[INFO] Detected {len(txt_files)} .txt files; starting processing.")

        for path in txt_files:
            no_value = path.stem  # Use filename stem as the "no" value.
            self.logger.debug(f"[DEBUG] Processing file: {path.name} (no={no_value})")

            data = self._load_single_txt(path)
            if data is None:
                continue

            record = self._flatten_json(data, no_value=no_value)
            records.append(record)

        self.logger.info(f"[INFO] Successfully parsed {len(records)} valid records.")
        return records

    def _cast_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert the "no" column and all score columns to integer type (Int64).

        Score columns are defined as:
        - All columns whose names end with "_score".
        - The column "total_quality_score".

        Conversion rules:
        - "no" column: if any value cannot be converted to a number, log an error
          and raise an exception.
        - Score columns: use pd.to_numeric(errors="coerce"); invalid values are
          set to <NA> and cast to Int64.

        :param df: Merged DataFrame.
        :return: DataFrame with normalized integer columns.
        :raises ValueError: If the "no" column contains non-numeric values.
        """
        df_cast = df.copy()

        # 1) Process "no" column (primary key, must be convertible to integer).
        if "no" in df_cast.columns:
            no_numeric = pd.to_numeric(df_cast["no"], errors="coerce")
            if no_numeric.isna().any():
                bad_values = df_cast.loc[no_numeric.isna(), "no"].unique()
                self.logger.error(
                    f"[ERROR] Non-integer values found in column 'no': {bad_values.tolist()}"
                )
                raise ValueError("Non-numeric values found in column 'no'; please check filenames.")
            df_cast["no"] = no_numeric.astype("Int64")

        # 2) Process score columns (all *_score + total_quality_score).
        score_cols: List[str] = [
            col
            for col in df_cast.columns
            if col.endswith("_score") or col == "total_quality_score"
        ]

        for col in score_cols:
            numeric_series = pd.to_numeric(df_cast[col], errors="coerce")
            df_cast[col] = numeric_series.astype("Int64")

        return df_cast

    def _sort_by_no_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort rows in ascending order by the "no" column.

        Notes:
        - This method assumes that the "no" column has already been converted
          to Int64 via _cast_numeric_columns.
        - If there is no "no" column, the original row order is preserved.

        :param df: Merged DataFrame.
        :return: DataFrame sorted by "no" in ascending order.
        """
        if "no" not in df.columns:
            return df

        return df.sort_values(by="no", ascending=True, kind="stable")

    def _log_missing_stats(self, df: pd.DataFrame) -> None:
        """
        Compute and log missingness statistics for each column
        (empty string / whitespace-only / NaN).

        Missingness definition:
        - NaN / None in the DataFrame.
        - Cells containing only whitespace or empty strings.

        :param df: Final merged DataFrame.
        :return: None
        """
        if df.empty:
            self.logger.info("[INFO] DataFrame is empty; skipping missingness statistics.")
            return

        df_missing = df.replace(r"^\s*$", pd.NA, regex=True)
        missing_counts = df_missing.isna().sum()
        total_rows = len(df_missing)

        self.logger.info("[STATS] Column-wise missing values (count / proportion):")
        for col in missing_counts.index:
            count = int(missing_counts[col])
            ratio = count / total_rows if total_rows > 0 else 0.0
            self.logger.info(
                f"[STATS] Column '{col}': missing {count} entries, {ratio:.2%} of rows"
            )

    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reorder columns according to the predefined logical order.

        Column grouping logic:
        1. Key metadata and identifiers (no, study_id, year, etc.).
        2. Overall quality scores and inclusion decisions.
        3. Item-level quality scores (score followed by notes).
        4. All remaining columns not listed in PREFERRED_COLUMN_ORDER,
           appended at the end in alphabetical order.

        :param df: Merged DataFrame.
        :return: DataFrame with optimized column order.
        """
        existing_cols = list(df.columns)

        # Keep only columns from PREFERRED_COLUMN_ORDER that actually exist.
        ordered: List[str] = [
            col for col in self.PREFERRED_COLUMN_ORDER if col in existing_cols
        ]

        # Append all remaining columns that are not in the preferred order.
        extra_cols = [col for col in existing_cols if col not in ordered]
        extra_cols_sorted = sorted(extra_cols)

        final_order = ordered + extra_cols_sorted
        return df.reindex(columns=final_order)

    def run(self) -> None:
        """
        Main execution entry point:
        - Read .txt files.
        - Merge flattened records.
        - Normalize numeric columns.
        - Reorder columns.
        - Sort by "no".
        - Log missingness statistics.
        - Write Excel output.

        :return: None
        :raises Exception: Propagates exceptions from type casting or file export.
        """
        records = self._collect_records()
        if not records:
            self.logger.warning(
                "[WARN] No valid records collected; "
                "quality_assessment_table.xlsx will not be created."
            )
            return

        # 1. Build DataFrame.
        df = pd.DataFrame(records)

        # 2. Convert "no" and all score columns to Int64 integer type.
        df = self._cast_numeric_columns(df)

        # 3. Reorder columns according to the predefined logical order.
        df = self._reorder_columns(df)

        # 4. Sort rows by "no" in ascending order (final ordering before export).
        df = self._sort_by_no_column(df)

        # 5. Log missingness statistics based on the final structure, to match Excel.
        self._log_missing_stats(df)

        # 6. Write Excel output.
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_excel(self.output_path, index=False)
            self.logger.info(
                f"[EXPORT] Merged quality assessment table written to: {self.output_path} "
                f"| rows: {len(df)} | columns: {len(df.columns)}"
            )
        except Exception as exc:
            self.logger.error(
                f"[ERROR] Failed to write Excel file: {self.output_path} | Error: {exc}"
            )
            raise


def main() -> None:
    """
    Script entry point: merge all JSON-style .txt quality assessment files
    into a single Excel table.

    :return: None
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] quality_assessment_texts_merger started.")

    merger = QualityAssessmentTextsMerger(logger=logger)
    merger.run()

    logger.info("[MAIN] quality_assessment_texts_merger finished.")


if __name__ == "__main__":
    main()
