"""
merge_and_deduplicat.py

This module provides utilities for merging multiple Excel files containing
search results from different databases, normalizing title case,
deduplicating records based on 'Article Title' and 'Publication Year',
rebuilding the 'No.' column, inspecting missing values, and writing the
merged and deduplicated data back to disk.

Typical workflow
----------------
1. Read raw Excel files from multiple databases (e.g. IEEE Xplore, ERIC,
   Scopus, Web of Science).
2. Normalize 'Article Title' and 'Publication Title' into a consistent
   title-style capitalization.
3. Normalize 'Publication Year' values to a four-digit 'YYYY' string.
4. Filter out records with 'Publication Year' < 2017.
5. Deduplicate records using ['Article Title', 'Publication Year'] as
   composite keys.
6. Rebuild the 'No.' column as a 1-based consecutive index.
7. Optionally inspect missing values for each column.
8. Save the merged and deduplicated dataset as a new Excel file.

The main entry point is process_data(), which resolves paths, runs the
pipeline, and saves the final file:
    data/systematic_review/raw/merged_and_deduplicated_data.xlsx

Author: SmartMahua <zhinengmahua@gmail.com>
Date: 2025-05-22
"""

import pandas as pd
from pathlib import Path


class DataMerger:
    """
    This class merges multiple Excel files, normalizes title case, and
    deduplicates rows based on 'Article Title' and 'Publication Year'.
    After deduplication, it rebuilds the 'No.' column and handles missing values.
    """

    # Preferred column order (can be adjusted as needed).
    PREFERRED_COLUMN_ORDER = [
        "No.",
        "Authors",
        "Article Title",
        "Publication Title",
        "Publication Year",
        "Abstract",
        "DOI",
        "Document Type",
        "Open Access",
        "Link",
    ]

    def __init__(self, file_paths: list[Path], small_words_file: Path) -> None:
        """
        :param file_paths: List of Excel file paths to be merged.
        :param small_words_file: Path to a text file containing "small words"
                                 (e.g., conjunctions, prepositions) that should
                                 remain lowercase in title case.
        """
        self.file_paths = file_paths
        self.small_words = self._load_small_words(small_words_file)

    def _load_small_words(self, small_words_file: Path) -> set:
        """
        Load words from small_words.txt that should not be capitalized
        in title case (e.g., conjunctions, prepositions).

        :param small_words_file: Path to small_words.txt.
        :return: A set of small words that should remain lowercase.
        """
        if not small_words_file.exists():
            raise FileNotFoundError(f"Small-words file {small_words_file} does not exist!")

        with open(small_words_file, "r", encoding="utf-8") as f:
            return set(line.strip().lower() for line in f)

    # -------------------- public API -------------------- #

    def merge_and_deduplicate(self) -> pd.DataFrame:
        """
        Merge all Excel files, deduplicate based on 'Article Title'
        and 'Publication Year', and regenerate the 'No.' column.

        :return: Deduplicated DataFrame with a rebuilt 'No.' column.
        """
        print("[INFO] Start reading and processing files...")
        dfs: list[pd.DataFrame] = []

        # Track row counts from each database/file.
        file_data_counts: dict[str, int] = {}

        for file_path in self.file_paths:
            if Path(file_path).exists():
                print(f"[INFO] Reading file: {file_path}")
                df = self._read_and_process_file(file_path)
                if not df.empty:
                    file_data_counts[file_path.name] = len(df)
                    dfs.append(df)
            else:
                print(f"[WARN] File not found, skipped: {file_path}")

        if not dfs:
            raise ValueError("No valid file data found. Please check the file paths.")

        # Concatenate all DataFrames.
        merged_df = pd.concat(dfs, ignore_index=True)
        print(f"[INFO] Successfully merged {len(dfs)} files.")
        print(f"[INFO] Total row count after merge: {len(merged_df)}")

        # Print row count from each database/file.
        for file, count in file_data_counts.items():
            print(f"[INFO] File '{file}' row count: {count}")

        # Filter out rows with 'Publication Year' < 2017.
        merged_df["Publication Year"] = pd.to_numeric(
            merged_df["Publication Year"], errors="coerce"
        )
        merged_df = merged_df[merged_df["Publication Year"] >= 2017]
        print(
            f"[INFO] After filtering 'Publication Year' < 2017, "
            f"{len(merged_df)} rows remain."
        )

        # Print missing-value status before deduplication.
        self._print_missing_values(merged_df)

        # Print row count before deduplication.
        print(f"[INFO] Row count before deduplication: {len(merged_df)}")

        # Deduplicate by 'Article Title' and 'Publication Year'.
        print("[INFO] Deduplicating data...")
        deduplicated_df = merged_df.drop_duplicates(
            subset=["Article Title", "Publication Year"], keep="first"
        )

        # Print row count after deduplication.
        print(f"[INFO] Row count after deduplication: {len(deduplicated_df)}")

        # Sort by 'Publication Year' in descending order.
        print("[INFO] Sorting by 'Publication Year' in descending order...")
        deduplicated_df = (
            deduplicated_df.sort_values(by="Publication Year", ascending=False)
            .reset_index(drop=True)
        )

        # Rebuild the 'No.' column.
        deduplicated_df = self._reindex_no_column(deduplicated_df)

        # Print missing-value status after deduplication.
        print("[INFO] After deduplication, checking missing values...")
        self._print_missing_values(deduplicated_df)

        # Fill missing values.
        print("[INFO] Filling missing values...")
        deduplicated_df = self._fill_missing_values(deduplicated_df, merged_df)

        # Print missing-value status after filling.
        print("[INFO] After filling, missing-value summary:")
        self._print_missing_values(deduplicated_df)

        print(f"[INFO] Deduplication complete; {len(deduplicated_df)} rows retained.")
        return deduplicated_df

    def save_to_excel(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Save the deduplicated DataFrame to an Excel file.

        :param df: DataFrame to be saved.
        :param output_path: Output Excel file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(output_path, index=False, engine="openpyxl")
        print(f"[INFO] Data successfully saved to {output_path}")

    # -------------------- internal helpers -------------------- #

    def _read_and_process_file(self, file_path: Path) -> pd.DataFrame:
        """
        Read an Excel file and normalize:
        - 'Article Title' and 'Publication Title' using title-style capitalization.
        - 'Publication Year' to the 'YYYY' format.

        :param file_path: Path to the Excel file to read.
        :return: Processed DataFrame.
        """
        df = pd.read_excel(file_path)

        # If 'Article Title' is missing, skip this file.
        if "Article Title" not in df.columns:
            print(f"[WARN] Column 'Article Title' is missing; skipping file: {file_path.name}")
            return pd.DataFrame()

        # Normalize title case for article and publication titles.
        df["Article Title"] = df["Article Title"].apply(self._capitalize_words)
        if "Publication Title" in df.columns:
            df["Publication Title"] = df["Publication Title"].apply(self._capitalize_words)

        # Normalize 'Publication Year' to 'YYYY' if it appears as a date-like numeric.
        if "Publication Year" in df.columns:
            df["Publication Year"] = df["Publication Year"].apply(self._convert_to_year)

        return df

    def _capitalize_words(self, text: str) -> str:
        """
        Apply title-style capitalization to a string while respecting the
        small-words list. Non-string inputs and NaN are handled gracefully.

        :param text: Input string to format.
        :return: Title-cased string; non-strings are returned unchanged, and
                 NaN/None is returned as an empty string.
        """
        if isinstance(text, str):
            words = text.split()
            capitalized_words = []

            for i, word in enumerate(words):
                # Capitalize the first word or any word not in the small-words list.
                if i == 0 or word.lower() not in self.small_words:
                    capitalized_words.append(word.capitalize())
                else:
                    capitalized_words.append(word.lower())

            return " ".join(capitalized_words)

        # For non-string or missing values, return as-is if not NaN, else empty string.
        return text if pd.notna(text) else ""

    def _convert_to_year(self, year_value) -> str:
        """
        Normalize 'Publication Year' values to a four-digit year ('YYYY').
        If the value is given as 'YYYYMMDD', extract the first four digits.

        :param year_value: Value to convert.
        :return: Four-digit year string, or an empty string if the format
                 cannot be recognized.
        """
        if isinstance(year_value, (int, float)):
            year_str = str(int(year_value))
            if len(year_str) == 8:  # 'YYYYMMDD' format
                return year_str[:4]
            elif len(year_str) == 4:  # Already 'YYYY'
                return year_str
        return ""  # Return empty string if the format is not recognized.

    def _fill_missing_values(
        self, deduplicated_df: pd.DataFrame, merged_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Fill missing values in the deduplicated DataFrame by looking up
        rows in the merged DataFrame that share the same 'Article Title'
        and 'Publication Year'.

        For each missing cell, if there exists a non-null value in any
        matching row, the first such value is used for imputation.

        :param deduplicated_df: DataFrame after deduplication.
        :param merged_df: Original merged DataFrame before deduplication.
        :return: DataFrame with missing values filled where possible.
        """
        for idx, row in deduplicated_df.iterrows():
            article_title = row["Article Title"]
            publication_year = row["Publication Year"]

            # Find all rows in the merged data with the same title and year.
            matching_rows = merged_df[
                (merged_df["Article Title"] == article_title)
                & (merged_df["Publication Year"] == publication_year)
            ]

            for col in deduplicated_df.columns:
                if pd.isna(row[col]) and col in matching_rows.columns:
                    non_null_values = matching_rows[col].dropna()
                    if not non_null_values.empty:
                        deduplicated_df.at[idx, col] = non_null_values.iloc[0]

        return deduplicated_df

    def _print_missing_values(self, df: pd.DataFrame) -> None:
        """
        Print the number of missing values in each column, along with the
        1-based row indices where missing values occur.

        :param df: DataFrame to inspect.
        """
        missing_values = df.isnull().sum()
        for col, missing in missing_values.items():
            if missing > 0:
                # Use index + 1 to align with human-readable row numbering.
                missing_indices = df[df[col].isnull()].index + 1
                print(
                    f"[MISSING] {col}: {missing} missing values, "
                    f"rows: {list(missing_indices)}"
                )

    def _reindex_no_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rebuild the 'No.' column to ensure it provides a 1-based consecutive
        index for all rows.

        :param df: DataFrame after deduplication.
        :return: DataFrame with a rebuilt 'No.' column.
        """
        df = df.copy()
        if "No." in df.columns:
            df = df.drop(columns=["No."])

        df.insert(0, "No.", range(1, len(df) + 1))
        return df

    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reorder the DataFrame columns according to PREFERRED_COLUMN_ORDER,
        appending any remaining columns afterward.

        :param df: DataFrame whose columns should be reordered.
        :return: DataFrame with columns reordered.
        """
        current_cols = list(df.columns)
        preferred_existing = [c for c in self.PREFERRED_COLUMN_ORDER if c in current_cols]
        remaining = [c for c in current_cols if c not in preferred_existing]
        new_order = preferred_existing + remaining
        return df[new_order]


def process_data() -> None:
    """
    Top-level function that:
    - Resolves the project root.
    - Collects all raw Excel files from the 'raw' directory.
    - Merges and deduplicates the data.
    - Saves the result as 'merged_and_deduplicated_data.xlsx'.
    """
    print("[INFO] Starting data processing...")

    project_root = Path(__file__).resolve().parents[3]
    data_dir = project_root / "data/systematic_review" / "raw"
    file_names = ["ieee_xplore.xlsx", "eric.xlsx", "scopus.xlsx", "web_of_science.xlsx"]
    file_paths = [data_dir / name for name in file_names]

    # Path to small_words.txt.
    small_words_file = project_root / "data/systematic_review" / "small_words.txt"

    # Create a DataMerger instance and process data.
    merger = DataMerger(file_paths, small_words_file)
    merged_df = merger.merge_and_deduplicate()

    output_path = data_dir / "merged_and_deduplicated_data.xlsx"
    merger.save_to_excel(merged_df, output_path)


if __name__ == "__main__":
    process_data()