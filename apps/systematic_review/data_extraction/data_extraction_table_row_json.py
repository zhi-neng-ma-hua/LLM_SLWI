# -*- coding: utf-8 -*-
"""
data_extraction_table_row_json.py

Purpose
-------
This script reads the data/systematic_review/data_extraction/data_extraction_table.xlsx file,
and converts each row of the table into a JSON object, printing each line with indentation
for easy review and debugging.

Core Features
-------------
1. Resolves the project root directory;
2. Reads the data_extraction_table.xlsx file;
3. Converts each row into a dictionary and formats it as a JSON string (with 4-space indentation and no escape for Chinese characters);
4. Prints the JSON data line by line in the terminal with clear separators.

Author: Aiden Cao <zhinengmahua@gmail.com>
Date: 2025-07-13
"""

import json
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
from apps.systematic_review.utils.logger_manager import LoggerManager


def setup_logger(
    name: str = "data_extraction_table_row_json",
    verbose: bool = True,
) -> logging.Logger:
    """
    Set up a standard logger for the application.

    :param name: Name of the logger
    :param verbose: Whether to enable DEBUG logging
    :return: logging.Logger object
    :raises Exception: Any exception will be raised by LoggerManager.setup_logger
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class DataExtractionTableRowPrinter:
    """
    A controller for printing rows of the data_extraction_table.xlsx as JSON.

    Workflow:
    1. Resolves the paths for the project root and data_extraction_table.xlsx;
    2. Reads the Excel file into a DataFrame;
    3. Converts each row into a dictionary and formats it as a JSON string with indentation;
    4. Prints each row with a separator between rows.
    """

    EXCEL_FILENAME = "data_extraction_table.xlsx"
    ROW_SEPARATOR = "-" * 70

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initializes the controller, resolves paths, and sets up the logger.

        :param logger: Logger instance; defaults to the default logger if None
        :raises FileNotFoundError: If the Excel file does not exist
        """
        self.logger = logger or setup_logger()
        self._init_paths()

    def _init_paths(self) -> None:
        """
        Resolves the path for the data_extraction_table.xlsx file.

        :return: None
        :raises FileNotFoundError: If the Excel file does not exist
        """
        # Resolve paths to the project root directory
        project_root = Path(__file__).resolve().parents[3]
        base_data_dir = project_root / "data" / "systematic_review" / "data_extraction"

        self.excel_path = base_data_dir / self.EXCEL_FILENAME

        if not self.excel_path.is_file():
            raise FileNotFoundError(f"Data extraction table not found: {self.excel_path}")

        self.logger.info(f"[PATH] Data extraction table path: {self.excel_path}")

    def _load_table(self) -> pd.DataFrame:
        """
        Loads the data_extraction_table.xlsx into a DataFrame.

        :return: DataFrame containing the data extraction results
        :raises Exception: If reading the Excel file fails, raises the underlying exception
        """
        self.logger.info("[INFO] Reading data_extraction_table.xlsx ...")
        try:
            df = pd.read_excel(self.excel_path)
            self.logger.info(f"[INFO] Read complete: Rows={len(df)}, Columns={len(df.columns)}")
            return df
        except Exception as exc:
            self.logger.error(f"[ERROR] Failed to read Excel file: {self.excel_path} | Error: {exc}")
            raise

    @staticmethod
    def _row_to_pretty_json(row: pd.Series) -> str:
        """
        Converts a single row into a formatted JSON string.

        :param row: A single row from the DataFrame (pd.Series)
        :return: The formatted JSON string (with 4-space indentation and no escape for Chinese characters)
        """
        data_dict = row.to_dict()
        return json.dumps(data_dict, ensure_ascii=False, indent=4)

    def print_rows_as_json(self) -> None:
        """
        Prints each row of the data_extraction_table.xlsx file as a JSON object.

        Example output:
        ----------------------------------------------------------------------
        Row 1 | No. = 001
        {
            "No.": "001",
            "Basic Identification.author": "...",
            ...
        }
        ----------------------------------------------------------------------
        Row 2 | No. = 002
        ...
        :return: None
        """
        df = self._load_table()

        # Only print rows from the 60th index onwards (as per the original code)
        df = df[60:]

        if df.empty:
            self.logger.warning("[WARN] The data table is empty, no rows printed.")
            return

        # Check if there is a "No." column for displaying row numbers
        has_no_col = "No." in df.columns

        for idx, row in df.iterrows():
            row_number = idx + 1  # Start row numbers from 1 for human-readable format
            no_value = row.get("No.", "") if has_no_col else ""

            # Print the separator and row number
            print(self.ROW_SEPARATOR)
            if has_no_col:
                print(f"Row {row_number} | No. = {no_value}")
            else:
                print(f"Row {row_number}")

            # Print the JSON formatted row
            pretty_json = self._row_to_pretty_json(row)
            print(pretty_json)

        print(self.ROW_SEPARATOR)
        self.logger.info("[INFO] All rows have been printed in JSON format.")

    def run(self) -> None:
        """
        Main entry point to read the data_extraction_table.xlsx and print each row as JSON.

        :return: None
        """
        self.print_rows_as_json()


def main() -> None:
    """
    Script entry point: Prints the contents of data_extraction_table.xlsx row by row in JSON format.

    :return: None
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] Starting data_extraction_table_row_json.")

    printer = DataExtractionTableRowPrinter(logger=logger)
    printer.run()

    logger.info("[MAIN] data_extraction_table_row_json execution completed.")


if __name__ == "__main__":
    main()
