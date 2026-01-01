
"""
Helper tools for file management.
"""
import logging
import os
import io
import base64
import pdfplumber
from typing import Optional, Union
from pathlib import Path
from ..config import TEMP_DATA_DIR

logger = logging.getLogger(__name__)


def get_file_name() -> str:
    """
    Gets the name of the first file in the temp-data folder.

    Returns:
        str: The name of the file, or an empty string if the folder is empty.
    """
    try:
        files = os.listdir(TEMP_DATA_DIR)
        if files:
            return files[0]
        return ""
    except FileNotFoundError:
        return ""


def extract_text_from_pdf(filename: str = None, file_content: bytes = None) -> str:
    """
    Extracts text from a PDF file.

    Args:
        filename: The name of the file in the temp-data folder.
        file_content: The content of the PDF file as bytes.

    Returns:
        The extracted text as a string.
    """
    if file_content:
        try:
            logger.info("Extracting text from PDF content.")
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                pdf_text = ""
                for page in pdf.pages:
                    pdf_text += page.extract_text()
            return pdf_text
        except Exception as e:
            logger.error("Error extracting text from PDF content: %s", e)
            return ""
    elif filename:
        try:
            file_path = TEMP_DATA_DIR / filename
            logger.info("Extracting text from PDF file %s", file_path)
            with pdfplumber.open(file_path) as pdf:
                pdf_text = ""
                for page in pdf.pages:
                    pdf_text += page.extract_text()
            return pdf_text
        except Exception as e:
            logger.error("Error extracting text from PDF: %s", e)
            return ""
    else:
        logger.error("Either filename or file_content must be provided.")
        return ""