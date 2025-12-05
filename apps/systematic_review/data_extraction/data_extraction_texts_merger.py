# -*- coding: utf-8 -*-
"""
data_extraction_texts_merger.py

Purpose
-------
This script merges all JSON-style .txt data extraction files from the
data/systematic_review/data_extraction/data_extraction_texts directory into a
single Excel file:

    data/systematic_review/data_extraction/data_extraction_table.xlsx

Core Features
-------------
1. Scans all .txt files in the specified directory;
2. Parses each .txt file into a JSON object;
3. Flattens nested JSON into a "wide-table" format;
4. Merges all records into a DataFrame;
5. Adds a "No." column, using the .txt filename prefix (excluding the extension);
6. Strips Chinese comments from field names and keeps only the English part;
7. Sorts by the "No." column in ascending order (using integer logic);
8. Exports the result to data_extraction_table.xlsx for subsequent data extraction and quality assessment.

Author: Aiden Cao <zhinengmahua@gmail.com>
Date: 2025-07-13
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from apps.systematic_review.utils.logger_manager import LoggerManager


def setup_logger(
    name: str = "data_extraction_texts_merger",
    verbose: bool = True,
) -> logging.Logger:
    """
    Setup a standard logger for the application.

    :param name: The name of the logger
    :param verbose: Whether to enable DEBUG logging
    :return: logging.Logger object
    :raises Exception: Any exceptions will be raised by LoggerManager.setup_logger
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class DataExtractionTextsMerger:
    """
    Controller for merging JSON-style .txt data extraction files.

    Workflow:
    1. Resolves project and data directory paths;
    2. Reads all .txt files from the data_extraction_texts/ directory;
    3. Parses each .txt file into a JSON object and flattens it to a single-line record;
    4. Strips Chinese comments from field names, retaining only the English part;
    5. Adds a "No." column (file name prefix), merges all records into a single DataFrame;
    6. Sorts the DataFrame by "No." in ascending order;
    7. Exports the merged table to data_extraction_table.xlsx.
    """

    INPUT_SUBDIR = "data_extraction_texts"
    OUTPUT_FILENAME = "data_extraction_table.xlsx"

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initializes the merger: resolves paths and sets up the logger.

        :param logger: Logger instance; defaults to the default logger if None
        :raises FileNotFoundError: If the input directory does not exist
        """
        self.logger = logger or setup_logger()
        self._init_paths()

    def _init_paths(self) -> None:
        """
        Resolves and checks input/output paths.

        :return: None
        :raises FileNotFoundError: If the TXT input directory does not exist
        """
        # Resolve paths to the project root directory
        project_root = Path(__file__).resolve().parents[3]
        base_data_dir = project_root / "data" / "systematic_review" / "data_extraction"

        self.input_dir = base_data_dir / self.INPUT_SUBDIR
        self.output_path = base_data_dir / self.OUTPUT_FILENAME

        if not self.input_dir.is_dir():
            raise FileNotFoundError(f"TXT input directory not found: {self.input_dir}")

        self.logger.info(
            f"[PATH] TXT input directory: {self.input_dir} | Output file: {self.output_path}"
        )

    @staticmethod
    def _clean_field_key(raw_key: str) -> str:
        """
        Cleans the field name, keeping only the English part (removes Chinese comments and parentheses).

        Example:
            "author (作者)" -> "author"
            "publication_year (发表年份)" -> "publication_year"

        :param raw_key: Raw field key (may contain Chinese comments)
        :return: Cleaned field name (only the English part)
        """
        cleaned = raw_key.split(" (", 1)[0].strip()
        return cleaned

    @staticmethod
    def _flatten_json(
        obj: Dict[str, Any],
        no_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Flattens a nested JSON object into a single-row wide-table dictionary.

        Example input JSON:
        {
          "Section A": {
              "author (作者)": "xxx",
              "publication_year (发表年份)": "2024"
          },
          "Section B": {
              "research_aims (研究目的与问题)": "...",
          }
        }

        Flattens to:
        {
          "No.": no_value,
          "Section A.author": "xxx",
          "Section A.publication_year": "2024",
          "Section B.research_aims": "..."
        }

        :param obj: JSON object representing a single record
        :param no_value: Value for the "No." column (typically the TXT file name prefix)
        :return: Flattened dictionary record
        """
        record: Dict[str, Any] = {}

        if no_value is not None:
            record["No."] = no_value

        for section, fields in obj.items():
            if not isinstance(fields, dict):
                record[str(section)] = fields
                continue

            for raw_key, value in fields.items():
                clean_key = DataExtractionTextsMerger._clean_field_key(str(raw_key))
                col_name = f"{section}.{clean_key}"
                record[col_name] = value

        return record

    def _load_single_txt(self, path: Path) -> Optional[Dict[str, Any]]:
        """
        Reads and parses a single .txt file into a JSON object.

        :param path: The .txt file path
        :return: Parsed JSON dictionary if successful, None if the file is empty or invalid
        """
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            self.logger.error(f"[ERROR] Unable to read file: {path} | Error: {exc}")
            return None

        if not text.strip():
            self.logger.warning(f"[WARN] File is empty or contains only whitespace, skipping: {path}")
            return None

        try:
            data = json.loads(text)
            return data
        except Exception as exc:
            self.logger.error(f"[ERROR] Cannot parse JSON from file: {path} | Error: {exc}")
            return None

    def _collect_records(self) -> List[Dict[str, Any]]:
        """
        Scans all .txt files and collects flattened records.

        :return: A list of flattened records, one for each .txt file
        """
        records: List[Dict[str, Any]] = []
        txt_files = sorted(self.input_dir.glob("*.txt"))

        if not txt_files:
            self.logger.warning(f"[WARN] No .txt files found in directory: {self.input_dir}")
            return records

        self.logger.info(f"[INFO] Found {len(txt_files)} .txt files, processing...")

        for path in txt_files:
            no_value = path.stem
            self.logger.debug(f"[DEBUG] Processing file: {path.name} (No.={no_value})")

            data = self._load_single_txt(path)
            if data is None:
                continue

            record = self._flatten_json(data, no_value=no_value)
            records.append(record)

        self.logger.info(f"[INFO] Successfully parsed {len(records)} valid records.")
        return records

    def _sort_by_no_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sorts the DataFrame by the "No." column in ascending order.

        :param df: The merged DataFrame
        :return: Sorted DataFrame by "No."
        """
        if "No." not in df.columns:
            return df

        no_numeric = pd.to_numeric(df["No."], errors="coerce")

        if no_numeric.isna().any():
            self.logger.warning(
                "[WARN] Non-numeric content found in 'No.' column, sorting by string order."
            )
            return df.sort_values(by="No.", ascending=True, kind="stable")

        df_sorted = df.copy()
        df_sorted["No."] = no_numeric.astype("Int64")
        df_sorted = df_sorted.sort_values(by="No.", ascending=True, kind="stable")

        return df_sorted

    def run(self) -> None:
        """
        Main entry point: Reads .txt files, merges records, and writes to Excel.

        :return: None
        :raises Exception: If writing to Excel fails, raises the underlying exception
        """
        records = self._collect_records()
        if not records:
            self.logger.warning(
                "[WARN] No valid records collected, data_extraction_table.xlsx will not be created."
            )
            return

        df = pd.DataFrame(records)

        df = self._sort_by_no_column(df)

        cols = list(df.columns)
        if "No." in cols:
            cols.remove("No.")
            ordered_cols = ["No."] + sorted(cols)
        else:
            ordered_cols = sorted(cols)
        df = df.reindex(columns=ordered_cols)

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_excel(self.output_path, index=False)
            self.logger.info(
                f"[EXPORT] Merged data extraction table written to: {self.output_path} "
                f"| Rows: {len(df)} | Columns: {len(df.columns)}"
            )
        except Exception as exc:
            self.logger.error(f"[ERROR] Failed to write Excel file: {self.output_path} | Error: {exc}")
            raise


def main() -> None:
    """
    Script entry point: Merges all JSON-style .txt data extraction files into a single Excel table.

    :return: None
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] Starting data_extraction_texts_merger.")

    merger = DataExtractionTextsMerger(logger=logger)
    merger.run()

    logger.info("[MAIN] data_extraction_texts_merger execution completed.")


if __name__ == "__main__":
    main()
