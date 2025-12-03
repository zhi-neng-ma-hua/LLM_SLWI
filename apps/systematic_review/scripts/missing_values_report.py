import pandas as pd
import os
from pathlib import Path


class TextFileWriter:
    """
    负责将统计报告写入到文本文件中的类。
    """

    def __init__(self, output_path):
        self.output_path = output_path

    def write_report(self, report):
        """
        将缺失值报告写入文本文件，确保每个文件间隔和格式合理美观。
        :param report: 缺失值统计报告字典
        """
        with open(self.output_path, "w", encoding="utf-8") as f:
            for file_name, missing_values in report.items():
                f.write(f"Report for file: {file_name}\n")
                f.write("-" * 50 + "\n")

                if missing_values:
                    for column, missing_rows in missing_values.items():
                        f.write(f"Column: {column}\n")
                        f.write(f"Missing rows (based on 'No.' column): {', '.join(map(str, missing_rows))}\n")
                        f.write("-" * 50 + "\n")
                else:
                    f.write("No missing values in any of the columns.\n")
                    f.write("-" * 50 + "\n")

                # Add a gap between each file report for clarity
                f.write("\n\n")


class MissingValueReporter:
    """
    负责统计 Excel 文件中各列的空值情况并返回缺失行号（行号来源于 "No." 列）的类。
    """

    def __init__(self, file_paths):
        self.file_paths = file_paths
        self.columns_of_interest = ["Authors", "Article Title", "Publication Title",
                                    "Publication Year", "Abstract", "DOI", "Link", "Document Type", "Open Access"]

    def report_missing_values(self):
        """
        遍历每个文件，统计每列的空值并输出缺失行号（行号来源于 "No." 列）。
        :return: 返回每个文件的缺失值统计结果和缺失行号
        """
        report = {}

        for file_path in self.file_paths:
            if os.path.exists(file_path):
                # 读取 Excel 文件
                df = pd.read_excel(file_path)

                # 检查并生成缺失值报告
                missing_report = self._generate_missing_report(df)
                if missing_report:
                    report[file_path.name] = missing_report

        return report

    def _generate_missing_report(self, df):
        """
        生成每列的缺失值统计报告，只列出缺失值的行号（行号来源于 "No." 列）。
        :param df: 读取的 DataFrame
        :return: 返回每列缺失值行号的字典
        """
        missing_report = {}
        if "No." not in df.columns:
            print("Warning: 'No.' column not found in file.")
            return missing_report

        for column in self.columns_of_interest:
            if column in df.columns:
                # 获取该列空值行的行号（基于 "No." 列）
                missing_rows = self._get_missing_rows(df, column)
                if missing_rows:
                    missing_report[column] = missing_rows
        return missing_report

    def _get_missing_rows(self, df, column):
        """
        获取缺失的行号，考虑到 'Abstract' 列的特殊情况（如 "[No abstract available]" 视为缺失值）。
        :param df: DataFrame
        :param column: 列名
        :return: 缺失值的行号列表
        """
        if column == "Abstract":
            # 将 "[No abstract available]" 视为缺失值
            missing_rows = df[df[column].isnull() | (df[column] == "[No abstract available]")].index + 1
        else:
            missing_rows = df[df[column].isnull()].index + 1

        return missing_rows.tolist()


def process_missing_values():
    """
    处理缺失值统计的主要函数，包括获取文件路径和调用报告函数。
    """
    print("开始统计缺失值...")

    # 获取项目根目录
    project_root = Path(__file__).resolve().parents[3]

    # 定义要检查的文件路径
    data_path = Path("data/systematic_review/raw")
    file_names = ["ieee_xplore.xlsx", "eric.xlsx", "scopus.xlsx", "web_of_science.xlsx", "merged_and_deduplicated_data.xlsx"]
    file_paths = [project_root / data_path / file_name for file_name in file_names]

    # 创建 MissingValueReporter 实例并统计空值
    reporter = MissingValueReporter(file_paths)
    missing_values_report = reporter.report_missing_values()

    # 定义输出报告路径
    output_report_path = project_root / data_path / "missing_values_report.txt"

    # 创建 TextFileWriter 实例并将报告写入文件
    writer = TextFileWriter(output_report_path)
    writer.write_report(missing_values_report)


if __name__ == "__main__":
    process_missing_values()