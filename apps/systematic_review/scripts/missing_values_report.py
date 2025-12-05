"""
missing_values_report.py

This module provides utilities for inspecting missing values in a set of
Excel files used in a systematic review workflow and writing a concise,
human-readable text report.

Core functionality
------------------
1. Read one or more Excel files (e.g. IEEE Xplore, ERIC, Scopus,
   Web of Science, and the merged/deduplicated dataset).
2. For each file, check a predefined list of key columns for missing values.
3. For each column with missing values, report the row identifiers based on
   the 'No.' column (rather than raw zero-based indices).
4. Treat a special placeholder in the 'Abstract' column
   ("[No abstract available]") as missing.
5. Write a structured plain-text report summarizing missing-value locations
   for each file to:
   data/systematic_review/raw/missing_values_report.txt

Author: SmartMahua <zhinengmahua@gmail.com>
Date: 2025-05-22
"""

import pandas as pd
import os
from pathlib import Path


class TextFileWriter:
    """
    Helper class responsible for writing a missing-value report to a text file.
    """

    def __init__(self, output_path):
        """
        :param output_path: Path to the output report file.
        """
        self.output_path = output_path

    def write_report(self, report):
        """
        Write the missing-value report dictionary to a text file, ensuring that
        the formatting is clear and visually separated between files.

        :param report: A dictionary mapping file name -> missing values summary,
                       where each summary is a dict:
                           {column_name: [list_of_missing_row_numbers]}
        """
        with open(self.output_path, "w", encoding="utf-8") as f:
            for file_name, missing_values in report.items():
                f.write(f"Report for file: {file_name}\n")
                f.write("-" * 50 + "\n")

                if missing_values:
                    for column, missing_rows in missing_values.items():
                        f.write(f"Column: {column}\n")
                        f.write(
                            "Missing rows (based on 'No.' column): "
                            f"{', '.join(map(str, missing_rows))}\n"
                        )
                        f.write("-" * 50 + "\n")
                else:
                    f.write("No missing values in any of the columns.\n")
                    f.write("-" * 50 + "\n")

                # Add a blank gap between each file report for readability
                f.write("\n\n")


class MissingValueReporter:
    """
    Class responsible for inspecting Excel files, computing column-wise
    missing-value locations, and returning the row identifiers based on
    the 'No.' column.
    """

    def __init__(self, file_paths):
        """
        :param file_paths: Iterable of file paths to Excel files to be checked.
        """
        self.file_paths = file_paths
        self.columns_of_interest = [
            "Authors",
            "Article Title",
            "Publication Title",
            "Publication Year",
            "Abstract",
            "DOI",
            "Link",
            "Document Type",
            "Open Access",
        ]

    def report_missing_values(self):
        """
        Iterate over each file and compute missing values for the columns
        of interest, reporting row numbers derived from the 'No.' column.

        :return: A dictionary mapping each file name to its missing-value
                 report (column -> list of missing-row indices).
        """
        report = {}

        for file_path in self.file_paths:
            if os.path.exists(file_path):
                # Read the Excel file
                df = pd.read_excel(file_path)

                # Generate the missing-value report for this file
                missing_report = self._generate_missing_report(df)
                if missing_report:
                    report[file_path.name] = missing_report

        return report

    def _generate_missing_report(self, df):
        """
        Generate a per-column missing-value report for a single DataFrame,
        reporting only the row numbers (derived from the 'No.' column).

        :param df: DataFrame read from an Excel file.
        :return: A dict mapping column name -> list of missing-row indices.
        """
        missing_report = {}
        if "No." not in df.columns:
            print("Warning: 'No.' column not found in file.")
            return missing_report

        for column in self.columns_of_interest:
            if column in df.columns:
                # Get missing row indices for the given column (based on 'No.')
                missing_rows = self._get_missing_rows(df, column)
                if missing_rows:
                    missing_report[column] = missing_rows
        return missing_report

    def _get_missing_rows(self, df, column):
        """
        Compute the list of row indices (1-based) with missing values in the
        specified column. For the 'Abstract' column, treat
        "[No abstract available]" as a missing value as well.

        :param df: DataFrame to inspect.
        :param column: Column name to check for missing values.
        :return: List of 1-based row indices where values are missing.
        """
        if column == "Abstract":
            # Treat "[No abstract available]" as a missing value.
            missing_rows = df[
                df[column].isnull() | (df[column] == "[No abstract available]")
            ].index + 1
        else:
            missing_rows = df[df[column].isnull()].index + 1

        return missing_rows.tolist()


def process_missing_values():
    """
    Main function orchestrating the missing-value analysis:
    - Resolve file paths for all relevant Excel files.
    - Run MissingValueReporter to compute missing-value locations.
    - Write the results to a text report using TextFileWriter.
    """
    print("[INFO] Starting missing-value analysis...")

    # Resolve project root directory
    project_root = Path(__file__).resolve().parents[3]

    # Define the Excel files to inspect
    data_path = Path("data/systematic_review/raw")
    file_names = [
        "ieee_xplore.xlsx",
        "eric.xlsx",
        "scopus.xlsx",
        "web_of_science.xlsx",
        "merged_and_deduplicated_data.xlsx",
    ]
    file_paths = [project_root / data_path / file_name for file_name in file_names]

    # Create a MissingValueReporter instance and compute missing-value statistics
    reporter = MissingValueReporter(file_paths)
    missing_values_report = reporter.report_missing_values()

    # Define the output path for the summary report
    output_report_path = project_root / data_path / "missing_values_report.txt"

    # Create a TextFileWriter instance and write the report to file
    writer = TextFileWriter(output_report_path)
    writer.write_report(missing_values_report)


if __name__ == "__main__":
    process_missing_values()