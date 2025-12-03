import pandas as pd
from pathlib import Path

class DataMerger:
    """
    该类负责合并多个 Excel 文件，标准化标题格式，并根据 'Article Title' 和 'Publication Year' 去重。
    同时，在去重后会重新编号 'No.' 列，并处理缺失值。
    """

    # 预定义列顺序（可按需要调整）
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

    def __init__(self, file_paths: list[Path], small_words_file: Path):
        """
        :param file_paths: 需要处理的 Excel 文件路径列表。
        :param small_words_file: 包含小词（小写字母）列表的文本文件路径。
        """
        self.file_paths = file_paths
        self.small_words = self._load_small_words(small_words_file)

    def _load_small_words(self, small_words_file: Path) -> set:
        """
        从 small_words.txt 文件中读取不需要大写的词（连词、介词等）。
        :param small_words_file: small_words.txt 文件路径
        :return: 小词的集合（不需要大写）
        """
        if not small_words_file.exists():
            raise FileNotFoundError(f"小词文件 {small_words_file} 不存在！")

        with open(small_words_file, 'r', encoding='utf-8') as f:
            return set(line.strip().lower() for line in f)

    # -------------------- public API -------------------- #

    def merge_and_deduplicate(self) -> pd.DataFrame:
        """
        合并所有 Excel 文件，并根据 'Article Title' 和 'Publication Year' 去重，重新生成 'No.' 列。
        :return: 合并去重后的 DataFrame，并重新编号 'No.' 列
        """
        print("开始读取和处理文件...")
        dfs = []

        # 统计每个数据库的数据量
        file_data_counts = {}

        for file_path in self.file_paths:
            if Path(file_path).exists():
                print(f"正在读取文件: {file_path}")
                df = self._read_and_process_file(file_path)
                if not df.empty:
                    file_data_counts[file_path.name] = len(df)
                    dfs.append(df)
            else:
                print(f"[WARN] 文件未找到，跳过: {file_path}")

        if not dfs:
            raise ValueError("没有有效的文件数据，请检查路径是否正确。")

        # 合并所有文件的数据
        merged_df = pd.concat(dfs, ignore_index=True)
        print(f"成功合并 {len(dfs)} 个文件。")
        print(f"合并后的总数据量: {len(merged_df)} 行数据。")

        # 打印每个数据库的数据量
        for file, count in file_data_counts.items():
            print(f"数据库 '{file}' 数据量: {count} 行")

        # 过滤 "Publication Year" 小于 2017 年的数据
        merged_df['Publication Year'] = pd.to_numeric(merged_df['Publication Year'], errors='coerce')
        merged_df = merged_df[merged_df['Publication Year'] >= 2017]
        print(f"过滤掉 'Publication Year' 小于 2017 年的数据后，共保留 {len(merged_df)} 行数据。")

        # 打印合并后的列空值情况
        self._print_missing_values(merged_df)

        # 打印去重前数据量
        print(f"去重前数据量: {len(merged_df)}")

        # 根据 'Article Title' 和 'Publication Year' 去重
        print("正在去重数据...")
        deduplicated_df = merged_df.drop_duplicates(subset=['Article Title', 'Publication Year'], keep='first')

        # 打印去重后的数据量
        print(f"去重后数据量: {len(deduplicated_df)}")

        # 按 'Publication Year' 降序排序
        print("正在按 'Publication Year' 降序排序数据...")
        deduplicated_df = deduplicated_df.sort_values(by="Publication Year", ascending=False).reset_index(drop=True)

        # 重新编号 'No.' 列
        deduplicated_df = self._reindex_no_column(deduplicated_df)

        # 打印去重后的列空值情况
        print("去重后，开始统计空值情况...")
        self._print_missing_values(deduplicated_df)

        # 填充缺失的值
        print("正在填充缺失值...")
        deduplicated_df = self._fill_missing_values(deduplicated_df, merged_df)

        # 打印填充后的空值情况
        print("填充后，空值情况统计：")
        self._print_missing_values(deduplicated_df)

        print(f"去重完成，共保留 {len(deduplicated_df)} 行数据。")
        return deduplicated_df

    def save_to_excel(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        将去重后的数据保存到 Excel 文件中。
        :param df: 需要保存的 DataFrame
        :param output_path: 输出的 Excel 文件路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(output_path, index=False, engine='openpyxl')
        print(f"[INFO] 数据成功保存到 {output_path}")

    # -------------------- internal helpers -------------------- #

    def _read_and_process_file(self, file_path: Path) -> pd.DataFrame:
        """
        读取 Excel 文件，并将 'Article Title' 和 'Publication Title' 中每个单词的首字母大写。
        处理 'Publication Year' 格式为 'YYYY'。
        :param file_path: 需要读取的 Excel 文件路径
        :return: 返回处理后的 DataFrame
        """
        df = pd.read_excel(file_path)

        # 如果 'Article Title' 列缺失，跳过该文件
        if 'Article Title' not in df.columns:
            print(f"[WARN] 'Article Title' 列缺失，跳过文件: {file_path.name}")
            return pd.DataFrame()

        # 标准化标题格式
        df['Article Title'] = df['Article Title'].apply(self._capitalize_words)
        if 'Publication Title' in df.columns:
            df['Publication Title'] = df['Publication Title'].apply(self._capitalize_words)

        # 处理 'Publication Year' 格式为 'YYYY'，如果存在日期格式
        if 'Publication Year' in df.columns:
            df['Publication Year'] = df['Publication Year'].apply(self._convert_to_year)

        return df

    def _capitalize_words(self, text: str) -> str:
        """
        根据标题式大小写规则，将每个单词首字母大写，处理 NaN 或非字符串输入。
        :param text: 需要格式化的字符串
        :return: 格式化后的字符串，非字符串返回原始数据
        """
        if isinstance(text, str):
            words = text.split()
            capitalized_words = []

            for i, word in enumerate(words):
                # 句首或非小词才大写
                if i == 0 or word.lower() not in self.small_words:
                    capitalized_words.append(word.capitalize())
                else:
                    capitalized_words.append(word.lower())

            return " ".join(capitalized_words)
        return text if pd.notna(text) else ''  # 非字符串或空值，直接返回原始值

    def _convert_to_year(self, year_value) -> str:
        """
        将 'Publication Year' 列的值格式化为年份（'YYYY'），如果是 'YYYYMMDD' 格式。
        :param year_value: 需要转换的值
        :return: 格式化后的年份
        """
        if isinstance(year_value, (int, float)):
            year_str = str(int(year_value))
            if len(year_str) == 8:  # 'YYYYMMDD' 格式
                return year_str[:4]
            elif len(year_str) == 4:  # 已是 'YYYY' 格式
                return year_str
        return ''  # 如果无法识别格式，返回空值

    def _fill_missing_values(self, deduplicated_df: pd.DataFrame, merged_df: pd.DataFrame) -> pd.DataFrame:
        """
        填充缺失的值：根据 'Article Title' 和 'Publication Year' 判断相同标题和年份的行是否存在数据，若有则填充。
        :param deduplicated_df: 去重后的 DataFrame
        :param merged_df: 合并的原始 DataFrame
        :return: 填充缺失值后的 DataFrame
        """
        for idx, row in deduplicated_df.iterrows():
            article_title = row["Article Title"]
            publication_year = row["Publication Year"]
            # 查找合并数据中所有相同标题和年份的行
            matching_rows = merged_df[(merged_df["Article Title"] == article_title) &
                                      (merged_df["Publication Year"] == publication_year)]

            for col in deduplicated_df.columns:
                if pd.isna(row[col]) and col in matching_rows.columns:
                    # 填充缺失值
                    non_null_values = matching_rows[col].dropna()
                    if not non_null_values.empty:
                        deduplicated_df.at[idx, col] = non_null_values.iloc[0]

        return deduplicated_df

    def _print_missing_values(self, df: pd.DataFrame) -> None:
        """
        打印每列的空值数量，并显示每个空值所在的 'No.'（索引）行。
        :param df: 要检查的 DataFrame
        """
        missing_values = df.isnull().sum()
        for col, missing in missing_values.items():
            if missing > 0:
                missing_indices = df[df[col].isnull()].index + 1  # 获取空值行的 'No.'（1-based）
                print(f"{col}: {missing} 个空值，空值所在行: {list(missing_indices)}")

    def _reindex_no_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        重新编号 'No.' 列，确保从 1 开始的连续编号。
        :param df: 去重后的 DataFrame
        :return: 重新编号后的 DataFrame
        """
        df = df.copy()
        if "No." in df.columns:
            df = df.drop(columns=["No."])

        df.insert(0, "No.", range(1, len(df) + 1))
        return df

    def _reorder_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        按照预定义的列顺序调整 DataFrame 的列顺序。
        :param df: 要调整的 DataFrame
        :return: 调整列顺序后的 DataFrame
        """
        current_cols = list(df.columns)
        preferred_existing = [c for c in self.PREFERRED_COLUMN_ORDER if c in current_cols]
        remaining = [c for c in current_cols if c not in preferred_existing]
        new_order = preferred_existing + remaining
        return df[new_order]


def process_data() -> None:
    """
    主函数，负责读取文件，合并数据，去重，并将结果保存到新的 Excel 文件中。
    """
    print("开始处理数据...")

    project_root = Path(__file__).resolve().parents[3]
    data_dir = project_root / "data/systematic_review" / "raw"
    file_names = ["ieee_xplore.xlsx", "eric.xlsx", "scopus.xlsx", "web_of_science.xlsx"]
    file_paths = [data_dir / name for name in file_names]

    small_words_file = project_root / "data/systematic_review/small_words.txt"  # small_words.txt 文件路径

    # 创建 DataMerger 实例并处理数据
    merger = DataMerger(file_paths, small_words_file)
    merged_df = merger.merge_and_deduplicate()

    output_path = data_dir / "merged_and_deduplicated_data.xlsx"
    merger.save_to_excel(merged_df, output_path)


if __name__ == "__main__":
    process_data()