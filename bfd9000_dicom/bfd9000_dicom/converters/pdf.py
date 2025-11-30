"""
PDF to DICOM converter.

Handles conversion of PDF documents to DICOM Encapsulated PDF format.
"""
import logging
from typing import Optional
from pydicom.dataset import Dataset
from pydicom.uid import EncapsulatedPDFStorage

from bfd9000_dicom.models import BaseDICOMMetadata
from .base import BaseConverter, ConversionError

logger = logging.getLogger(__name__)


class PDFConverter(BaseConverter):
    """
    Converter for PDF documents to DICOM Encapsulated PDF Storage.
    
    PDFs are encapsulated as binary data within DICOM, not converted to pixel data.
    The PDF file is embedded directly in the DICOM file.
    """
    
    @staticmethod
    def convert(
        metadata: BaseDICOMMetadata,
        input_path: str,
        output_path: Optional[str] = None,
        compression: bool = True  # Ignored for PDF, kept for API consistency
    ) -> Dataset:
        """
        Convert a PDF document to DICOM Encapsulated PDF format.
        
        Args:
            metadata: DICOM metadata DTO (should be DocumentMetadata)
            input_path: Path to input PDF file
            output_path: Optional path to save DICOM file
            compression: Ignored (PDF is already compressed internally)
        
        Returns:
            Complete DICOM Dataset with encapsulated PDF
            
        Raises:
            ConversionError: If PDF cannot be processed
        """
        # Validate input
        input_file = PDFConverter._validate_input_file(input_path)
        
        try:
            # Get base dataset from metadata
            ds = metadata.to_dataset()
            
            # Override SOP Class for Encapsulated PDF
            ds.SOPClassUID = EncapsulatedPDFStorage
            ds.file_meta.MediaStorageSOPClassUID = EncapsulatedPDFStorage
            
            # Read PDF as binary
            with open(input_file, 'rb') as f:
                pdf_bytes = f.read()
            
            # Encapsulate PDF in DICOM
            ds.EncapsulatedDocument = pdf_bytes
            ds.MIMETypeOfEncapsulatedDocument = "application/pdf"
            
            # Set document-specific attributes if available
            if hasattr(metadata, 'document_title') and metadata.document_title:
                ds.DocumentTitle = metadata.document_title
            
            logger.debug(f"Encapsulated PDF of {len(pdf_bytes)} bytes")
            
            # Save if output path provided
            if output_path:
                PDFConverter._save_dataset(ds, output_path)
                logger.info(f"Saved DICOM file: {output_path}")
            
            return ds
            
        except Exception as e:
            logger.error(f"Error converting PDF {input_path}: {e}")
            raise ConversionError(f"Failed to convert PDF: {e}") from e
