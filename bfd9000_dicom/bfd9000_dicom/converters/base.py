"""
Base converter interface for all file type converters.

All converters inherit from BaseConverter and implement the convert() method.
"""
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from pydicom.dataset import Dataset
from bfd9000_dicom.models import BaseDICOMMetadata


class BaseConverter(ABC):
    """
    Abstract base class for all file type converters.
    
    Converters are responsible for:
    1. Loading binary data from a file
    2. Processing/encoding the data appropriately
    3. Adding the encoded data to a DICOM Dataset
    4. Returning a complete, saveable DICOM Dataset
    
    Converters do NOT handle metadata - that comes from the metadata DTO.
    """
    
    @staticmethod
    @abstractmethod
    def convert(
        metadata: BaseDICOMMetadata,
        input_path: str,
        output_path: Optional[str] = None,
        compression: bool = True
    ) -> Dataset:
        """
        Convert a file to DICOM format.
        
        Args:
            metadata: DICOM metadata DTO (any subclass of BaseDICOMMetadata)
            input_path: Path to input file
            output_path: Optional path to save DICOM file. If None, doesn't save.
            compression: If True, use JPEG2000 lossless compression.
                        If False, use uncompressed transfer syntax (ExplicitVRLittleEndian).
        
        Returns:
            Complete DICOM Dataset with metadata and pixel/document data
        """
        pass
    
    @staticmethod
    def _save_dataset(ds: Dataset, output_path: str) -> None:
        """
        Save a DICOM dataset to file.
        
        Args:
            ds: DICOM Dataset to save
            output_path: Path where DICOM file should be saved
        """
        ds.save_as(output_path, write_like_original=False)
        
    @staticmethod
    def _validate_input_file(input_path: str) -> Path:
        """
        Validate that input file exists.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Path object for the input file
            
        Raises:
            FileNotFoundError: If input file doesn't exist
        """
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        return path


class UnsupportedFileTypeError(Exception):
    """Raised when a file type is not supported by any converter."""
    pass


class ConversionError(Exception):
    """Raised when a conversion operation fails."""
    pass
