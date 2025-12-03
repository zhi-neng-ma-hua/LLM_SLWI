# -*- coding: utf-8 -*-
"""
exceptions.py

自定义异常体系模块（项目全局通用）

本模块定义了项目所有自定义异常的统一基类和常用派生异常，适用于批量数据处理、PDF 解析、
参数校验等业务场景。统一的异常体系便于全局捕获、日志管理、团队协作、自动化运维和问题溯源。

主要异常类：
    - BaseAppException      ：项目根异常，所有自定义异常应继承自此类
    - PdfExtractError       ：PDF 文本解析与抽取业务异常
    - DataValidationError   ：参数与数据前置校验异常
    - BatchProcessingError  ：批量流程顶级业务异常

作者：智能麻花 <zhinengmahua@gmail.com>
日期：2025-05-22
"""

from typing import Optional


class BaseAppException(Exception):
    """
    项目自定义异常的统一基类。

    用于构建统一的异常继承体系，实现全局异常捕获与链式溯源。
    推荐所有自定义异常均继承此类，以支持日志归档、团队协作和运维监控。
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        初始化 BaseAppException。

        :param message: 错误描述信息（建议英文/国际化）
        :param cause:   可选，底层触发的原始异常 Exception
        """
        super().__init__(message)
        self.cause = cause

    def __str__(self):
        base = super().__str__()
        return f"{base} (caused by {repr(self.cause)})" if self.cause else base


class PdfExtractError(BaseAppException):
    """
    PDF 文本解析与抽取业务异常。

    用于封装 PDF 文件解析、内容提取、格式损坏等所有与 PDF 处理相关的业务错误，
    仅由业务流程统一捕获，便于日志溯源与异常分析。
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        初始化 PdfExtractError。

        :param message: 错误描述信息（建议英文/国际化）
        :param cause:   可选，底层触发的原始异常 Exception
        """
        super().__init__(message, cause)


class DataValidationError(BaseAppException):
    """
    参数与数据前置校验异常。

    专用于参数、路径、类型、配置、数据有效性等前置校验环节的异常处理。
    与业务性 PdfExtractError 明确解耦，用于输入校验保障。
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        初始化 DataValidationError。

        :param message: 错误描述信息
        :param cause:   可选，底层触发的原始异常 Exception
        :raises TypeError: 若 message 不是 str
        """
        if not isinstance(message, str):
            raise TypeError("DataValidationError 'message' must be str")
        super().__init__(message, cause)


class BatchProcessingError(BaseAppException):
    """
    批量处理流程顶级业务异常。

    统一封装批量处理流程中的所有非参数性业务错误，
    适用于目录扫描、单个/多个文件处理、I/O 失败、业务流程异常等场景。
    支持异常链，便于日志溯源和全局统一捕获。
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        初始化 BatchProcessingError。

        :param message: 错误描述信息
        :param cause:   可选，底层触发的原始异常 Exception
        """
        super().__init__(message, cause)
