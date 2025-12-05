# -*- coding: utf-8 -*-
"""
exceptions.py

Custom exception hierarchy module (project-wide).

This module defines a unified base class and common derived exceptions
used across the project, suitable for batch data processing, PDF parsing,
parameter validation, and other business scenarios. A consistent exception
hierarchy facilitates centralized error handling, logging, team collaboration,
automated operations, and issue tracing.

Main exception classes:
    - BaseAppException      : Root exception for the project; all custom
                              exceptions should inherit from this class.
    - PdfExtractError       : Business exception for PDF text parsing
                              and extraction.
    - DataValidationError   : Exception for parameter and data pre-validation.
    - BatchProcessingError  : Top-level business exception for batch workflows.

Author: Aiden Cao <zhinengmahua@gmail.com>
Date: 2025-05-22
"""

from typing import Optional


class BaseAppException(Exception):
    """
    Unified base class for all custom application exceptions.

    This class provides a common inheritance root to enable global exception
    handling and chained error tracing. All custom exceptions are recommended
    to inherit from this class to support consistent logging, collaboration,
    and operations monitoring.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Initialize BaseAppException.

        :param message: Error description (preferably in English / i18n-friendly).
        :param cause:   Optional underlying Exception that triggered this error.
        """
        super().__init__(message)
        self.cause = cause

    def __str__(self):
        base = super().__str__()
        return f"{base} (caused by {repr(self.cause)})" if self.cause else base


class PdfExtractError(BaseAppException):
    """
    Business exception for PDF text parsing and extraction.

    Used to wrap all PDF-related errors such as parsing failures, content
    extraction issues, or corrupted file formats. This exception should be
    caught at the business layer only, to support centralized logging and
    error analysis.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Initialize PdfExtractError.

        :param message: Error description (preferably in English / i18n-friendly).
        :param cause:   Optional underlying Exception that triggered this error.
        """
        super().__init__(message, cause)


class DataValidationError(BaseAppException):
    """
    Exception for parameter and data pre-validation.

    Dedicated to errors in pre-validation steps, such as parameters, paths,
    types, configuration, and data integrity/validity. This is explicitly
    decoupled from business-level errors like PdfExtractError and focuses
    on guarding inputs and configuration.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Initialize DataValidationError.

        :param message: Error description.
        :param cause:   Optional underlying Exception that triggered this error.
        :raises TypeError: If message is not a str.
        """
        if not isinstance(message, str):
            raise TypeError("DataValidationError 'message' must be str")
        super().__init__(message, cause)


class BatchProcessingError(BaseAppException):
    """
    Top-level business exception for batch processing workflows.

    Used to wrap all non-validation business errors in batch pipelines,
    including directory scanning, single/multi-file processing, I/O failures,
    and other workflow-related issues. Supports exception chaining to aid
    logging, tracing, and global unified error handling.
    """

    def __init__(self, message: str, cause: Optional[Exception] = None):
        """
        Initialize BatchProcessingError.

        :param message: Error description.
        :param cause:   Optional underlying Exception that triggered this error.
        """
        super().__init__(message, cause)