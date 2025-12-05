# -*- coding: utf-8 -*-
"""
document_type_statistics.py

This module provides a small utility for post-processing a merged,
deduplicated search result Excel file used in a systematic review.

Core functionality
------------------
1. Read the Excel file from:
       data/systematic_review/raw/merged_and_deduplicated_data.xlsx
   under the project root.
2. Normalize the values in the 'Document Type' column:
   - Map a variety of source-specific document types to a small set of
     standard labels (e.g. "Conference Paper", "Journal Article", "Early Access").
   - Treat all values starting with "Journal Articles" as "Journal Article".
3. Filter rows by document type, keeping:
   - "Journal Article"
   - "Conference Paper"
   - "Early Access"
   - and the specific pattern
     "Journal Articles : Information Analyses : Reports - Research".
4. Rebuild the 'No.' column as a 1-based consecutive index.
5. Overwrite the original Excel file with the cleaned data.

The script can be run directly from the command line, or imported and used
programmatically via the DocumentTypeStatistics class.

Author: SmartMahua <zhinengmahua@gmail.com>
Date: 2025-05-22
"""

import pandas as pd
from pathlib import Path
import re


class DocumentTypeStatistics:
    """
    This class reads an Excel file, normalizes the 'Document Type' column,
    filters rows by predefined criteria, and writes the cleaned data back to disk.
    """

    # Mapping table for normalizing raw 'Document Type' values to standard labels.
    document_type_map = {
        "IEEE Conferences": "Conference Paper",
        "Conference paper": "Conference Paper",
        "Proceedings Paper": "Conference Paper",
        "Conference review": "Conference Paper",
        "IEEE Journals": "Journal Article",
        "IEEE Early Access Articles": "Early Access",
        "Article": "Journal Article",
        "Article; Early Access": "Early Access",
        "Article; Retracted Publication": "Retracted",
        "Retracted": "Retracted",
        "Review": "Review",
        "Book chapter": "Book Chapter",
        "Book": "Book",
        "Editorial Material": "Editorial",
        "Note": "Note",
        "Erratum": "Erratum",
        "Letter": "Letter",
        "Article; Book Chapter": "Book Chapter",
    }

    def __init__(self, input_file_path: Path) -> None:
        """
        Initialize a DocumentTypeStatistics instance.

        :param input_file_path: Path to the Excel file to be processed.
        """
        self.input_file_path = input_file_path

    def read_and_statistic(self) -> None:
        """
        Read the Excel file, normalize the 'Document Type' column, filter
        rows according to predefined rules, print basic statistics to stdout,
        and overwrite the original Excel file with the cleaned data.
        """
        # Read Excel file
        print(f"[INFO] Reading file: {self.input_file_path}")
        df = pd.read_excel(self.input_file_path)

        # Normalize and process the 'Document Type' column if present
        if "Document Type" in df.columns:
            df["Document Type"] = df["Document Type"].apply(self._standardize_document_type)
            print("\n[INFO] 'Document Type' column has been normalized.")

            # Print row count before filtering
            print(f"[INFO] Row count before filtering: {len(df)}")

            # Filter rows by document type
            df = self._filter_document_type(df)

            # Print statistics for 'Document Type' after filtering
            print("\n[INFO] 'Document Type' distribution after filtering:")
            print(df["Document Type"].value_counts())

            # Rebuild the 'No.' column
            df = self._reindex_no_column(df)

            # Save the modified data back to Excel
            self._save_to_excel(df)
        else:
            print("[WARN] Column 'Document Type' not found in the input file.")

    def _standardize_document_type(self, text: str) -> str:
        """
        Normalize raw 'Document Type' values using a mapping table and a
        special rule for values starting with "Journal Articles".

        - All values starting with "Journal Articles" are mapped to
          "Journal Article".
        - Remaining values are mapped using document_type_map; if no mapping
          is found, the stripped original value is kept.

        :param text: Raw 'Document Type' value.
        :return: Normalized 'Document Type' label.
        """
        if pd.isna(text):
            return text

        # First handle any type starting with "Journal Articles"
        if str(text).startswith("Journal Articles"):
            return "Journal Article"

        # Use the mapping table for standardization
        return self.document_type_map.get(str(text).strip(), str(text).strip())

    def _filter_document_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter the DataFrame by 'Document Type', keeping only specific types.

        Kept types:
        - "Journal Article"
        - "Conference Paper"
        - "Early Access"
        - plus any type containing the exact pattern
          "Journal Articles : Information Analyses : Reports - Research".

        :param df: DataFrame to be filtered.
        :return: Filtered DataFrame.
        """
        # Define the document types to keep
        valid_document_types = [
            "Journal Article",
            "Conference Paper",
            "Early Access",
        ]

        # Regular expression matching the special "Journal Articles..." type
        regex_pattern = r"Journal Articles : Information Analyses : Reports - Research"

        # Filter rows where 'Document Type' is one of the valid types,
        # or matches the special pattern
        df_filtered = df[
            df["Document Type"].isin(valid_document_types)
            | df["Document Type"].str.contains(regex_pattern, na=False)
        ]

        print(
            "[INFO] Kept document types: "
            f"{valid_document_types} + "
            "'Journal Articles : Information Analyses : Reports - Research'"
        )
        print(f"[INFO] Row count after filtering: {len(df_filtered)}")
        return df_filtered

    def _save_to_excel(self, df: pd.DataFrame) -> None:
        """
        Save the modified DataFrame back to the original Excel file.

        :param df: DataFrame to be saved.
        """
        df.to_excel(self.input_file_path, index=False, engine="openpyxl")
        print(f"[INFO] Data successfully written back to {self.input_file_path}")

    def _reindex_no_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rebuild the 'No.' column as a consecutive 1-based index.

        - If a 'No.' column already exists, it is dropped and recreated.

        :param df: DataFrame after filtering.
        :return: DataFrame with a reindexed 'No.' column.
        """
        df = df.copy()
        if "No." in df.columns:
            df = df.drop(columns=["No."])

        df.insert(0, "No.", range(1, len(df) + 1))
        print(f"[INFO] Reindexed 'No.' column; {len(df)} rows retained.")
        return df


def process_document_type_statistics() -> None:
    """
    Top-level helper function.

    Resolve the project root, locate the merged search result Excel file,
    and run DocumentTypeStatistics to normalize and filter the 'Document Type'
    column in-place.
    """
    # Resolve project root directory
    project_root = Path(__file__).resolve().parents[3]

    # Define data file path relative to the project root
    data_path = Path("data/systematic_review/raw")
    input_file_path = project_root / data_path / "merged_and_deduplicated_data.xlsx"

    # Create an instance of DocumentTypeStatistics and run the analysis
    stats = DocumentTypeStatistics(input_file_path)
    stats.read_and_statistic()


if __name__ == "__main__":
    process_document_type_statistics()