import pandas as pd
from pathlib import Path
import re


class DocumentTypeStatistics:
    """
    该类负责读取 Excel 文件并统计 'Document Type' 列的值及其数量，并根据指定条件进行过滤。
    """

    # 'Document Type' 映射
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
        "Article; Book Chapter": "Book Chapter"
    }

    def __init__(self, input_file_path: Path):
        """
        初始化 DocumentTypeStatistics 类，接受一个 Excel 文件路径作为参数。
        :param input_file_path: 需要读取的 Excel 文件路径
        """
        self.input_file_path = input_file_path

    def read_and_statistic(self):
        """
        读取 Excel 文件，统一 'Document Type' 列，并统计 'Document Type' 列的值及其数量。
        """
        # 读取 Excel 文件
        print(f"正在读取文件: {self.input_file_path}")
        df = pd.read_excel(self.input_file_path)

        # 统一 'Document Type' 列的命名
        if "Document Type" in df.columns:
            df['Document Type'] = df['Document Type'].apply(self._standardize_document_type)
            print("\nDocument Type 列数据已统一命名。")

            # 打印去重前的数据量
            print(f"去重前数据量: {len(df)}")

            # 过滤指定的 'Document Type' 值
            df = self._filter_document_type(df)

            # 打印去重后的 'Document Type' 数据统计
            print("\n过滤后的 Document Type 列数据统计：")
            print(df["Document Type"].value_counts())

            # 重新生成 'No.' 列
            df = self._reindex_no_column(df)

            # 保存修改后的数据到 Excel
            self._save_to_excel(df)
        else:
            print("[WARN] 'Document Type' 列未找到")

    def _standardize_document_type(self, text: str) -> str:
        """
        统一 'Document Type' 列的命名规范，映射不同的格式为标准化名称。
        同时，将所有以 "Journal Articles" 开头的文献类型统一为 "Journal Article"。
        :param text: 需要标准化的 'Document Type' 值
        :return: 标准化后的 'Document Type'
        """
        if pd.isna(text):
            return text

        # 首先处理所有以 "Journal Articles" 开头的文献类型
        if text.startswith("Journal Articles"):
            return "Journal Article"

        # 使用映射表进行统一
        return self.document_type_map.get(text.strip(), text.strip())

    def _filter_document_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据指定条件过滤 'Document Type' 列，保留特定的文献类型。
        :param df: 要过滤的 DataFrame
        :return: 过滤后的 DataFrame
        """
        # 定义要保留的文献类型
        valid_document_types = [
            "Journal Article",
            "Conference Paper",
            "Early Access"
        ]

        # 定义一个正则表达式模式，匹配包含 "Journal Articles : Information Analyses : Reports - Research" 的类型
        regex_pattern = r"Journal Articles : Information Analyses : Reports - Research"

        # 过滤 'Document Type' 列，保留指定的文献类型
        df_filtered = df[
            df["Document Type"].isin(valid_document_types) | df["Document Type"].str.contains(regex_pattern, na=False)]

        print(
            f"保留的文献类型: {valid_document_types} + 'Journal Articles : Information Analyses : Reports - Research'")
        print(f"过滤后，共保留 {len(df_filtered)} 行数据。")
        return df_filtered

    def _save_to_excel(self, df: pd.DataFrame):
        """
        将修改后的 DataFrame 保存到原 Excel 文件中。
        :param df: 需要保存的 DataFrame
        """
        df.to_excel(self.input_file_path, index=False, engine='openpyxl')
        print(f"[INFO] 数据已成功保存回 {self.input_file_path}")

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
        print(f"重新编号 'No.' 列，共保留 {len(df)} 行数据。")
        return df


def process_document_type_statistics():
    """
    主函数，负责读取数据文件并统一 'Document Type' 列的值，打印并保存修改后的数据。
    """
    # 获取项目根目录
    project_root = Path(__file__).resolve().parents[3]

    # 定义数据文件路径
    data_path = Path("data/systematic_review/raw")
    input_file_path = project_root / data_path / "merged_and_deduplicated_data.xlsx"

    # 创建 DocumentTypeStatistics 实例并统计 'Document Type' 列的值及其数量
    stats = DocumentTypeStatistics(input_file_path)
    stats.read_and_statistic()


if __name__ == "__main__":
    process_document_type_statistics()