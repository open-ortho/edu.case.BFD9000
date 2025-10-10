"""
DICOM metadata models (DTOs) for various imaging modalities.

These models provide a Django-like interface for building DICOM datasets.
Similar to Django models, they have methods like .to_dataset() that convert
the metadata into pydicom Dataset objects.

Usage:
    metadata = RadiographMetadata(
        patient_id="B0013",
        patient_sex=PatientSex.M,
        patient_age="217M"
    )
    ds = metadata.to_dataset()
    ds.save_as("output.dcm")
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import (
    ExplicitVRLittleEndian,
    SecondaryCaptureImageStorage,
    generate_uid
)


class PatientSex(Enum):
    """DICOM Patient Sex values (0010,0040)."""
    M = "M"  # Male
    F = "F"  # Female
    O = "O"  # Other
    U = "U"  # Unknown


class ModalityType(Enum):
    """DICOM Modality values (0008,0060)."""
    RG = "RG"  # Radiographic imaging (conventional film/screen)
    DX = "DX"  # Digital Radiography
    CR = "CR"  # Computed Radiography
    OT = "OT"  # Other
    DOC = "DOC"  # Document
    XC = "XC"  # External-camera Photography


class ConversionType(Enum):
    """DICOM Conversion Type values (0008,0064)."""
    DF = "DF"  # Digitized Film
    DI = "DI"  # Digital Interface
    SYN = "SYN"  # Synthetic Image


class BurnedInAnnotation(Enum):
    """DICOM Burned In Annotation values (0028,0301)."""
    YES = "YES"
    NO = "NO"


@dataclass
class BaseDICOMMetadata:
    """
    Base DICOM metadata for all imaging modalities.

    This class follows Django model conventions with methods to convert
    to pydicom Dataset objects. Maps to DICOM standard attributes using
    the official DICOM keywords.

    Attributes map to DICOM tags as follows:
        patient_id → PatientID (0010,0020)
        patient_sex → PatientSex (0010,0040)
        patient_age → PatientAge (0010,1010)
        patient_name → PatientName (0010,0010)
        patient_birth_date → PatientBirthDate (0010,0030)
        study_instance_uid → StudyInstanceUID (0020,000D)
        study_id → StudyID (0020,0010)
        study_date → StudyDate (0008,0020)
        study_time → StudyTime (0008,0030)
        series_instance_uid → SeriesInstanceUID (0020,000E)
        series_number → SeriesNumber (0020,0011)
        sop_instance_uid → SOPInstanceUID (0008,0018)
        sop_class_uid → SOPClassUID (0008,0016)
        instance_number → InstanceNumber (0020,0013)
        modality → Modality (0008,0060)
    """

    # Patient Information Module (required fields)
    patient_id: str
    patient_sex: PatientSex
    patient_age: str  # Format: "nnnM" for months or "nnnY" for years

    # Patient Information Module (optional fields)
    patient_name: Optional[str] = None
    patient_birth_date: str = ""  # YYYYMMDD format, empty for deidentified
    patient_identity_removed: str = "YES"
    deidentification_method: str = "Removed: Patient name, birthdate, study date/time."

    # Study Information Module
    study_instance_uid: Optional[str] = None
    study_id: str = "1"
    study_date: str = ""  # YYYYMMDD format, empty if unknown
    study_time: str = ""  # HHMMSS format, empty if unknown
    accession_number: str = ""
    referring_physician_name: str = ""

    # Series Information Module
    series_instance_uid: Optional[str] = None
    series_number: str = "1"
    modality: ModalityType = ModalityType.OT

    # Instance Information Module
    sop_instance_uid: Optional[str] = None
    sop_class_uid: str = SecondaryCaptureImageStorage
    instance_number: str = "1"

    # Secondary Capture Device Module
    secondary_capture_device_id: str = ""
    secondary_capture_device_manufacturer: str = ""
    secondary_capture_device_manufacturer_model_name: str = ""
    secondary_capture_device_software_versions: str = ""

    # General Image Module
    image_comments: str = ""

    # Image Plane Module
    image_position_patient: str = ""
    image_orientation_patient: str = ""
    patient_orientation: str = ""

    def __post_init__(self):
        """Auto-generate UIDs if not provided (Django-like save behavior)."""
        if self.study_instance_uid is None:
            self.study_instance_uid = generate_uid()
        if self.series_instance_uid is None:
            self.series_instance_uid = generate_uid()
        if self.sop_instance_uid is None:
            self.sop_instance_uid = generate_uid()

        # Auto-generate patient name if not provided
        if self.patient_name is None:
            self.patient_name = f"{self.patient_id}^Study Subject"

    def build_file_meta(self) -> FileMetaDataset:
        """
        Build DICOM File Meta Information.

        Returns:
            FileMetaDataset with appropriate Transfer Syntax and SOP Class
        """
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = self.sop_class_uid
        file_meta.MediaStorageSOPInstanceUID = self.sop_instance_uid
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        file_meta.ImplementationClassUID = generate_uid()
        return file_meta

    def to_dataset(self) -> Dataset:
        """
        Convert metadata to pydicom Dataset.

        This is the main conversion method, similar to Django's .save() method.
        Creates a complete DICOM dataset with all metadata fields.

        Returns:
            pydicom Dataset with all metadata populated
        """
        ds = Dataset()
        ds.file_meta = self.build_file_meta()

        # Add all DICOM modules
        self._add_patient_module(ds)
        self._add_study_module(ds)
        self._add_series_module(ds)
        self._add_instance_module(ds)
        self._add_device_module(ds)
        self._add_image_module(ds)

        return ds

    def _add_patient_module(self, ds: Dataset):
        """Add Patient Module attributes to dataset."""
        ds.PatientID = self.patient_id
        ds.PatientName = self.patient_name[:64] if self.patient_name else ""
        ds.PatientSex = self.patient_sex.value
        ds.PatientAge = self.patient_age
        ds.PatientBirthDate = self.patient_birth_date
        ds.PatientIdentityRemoved = self.patient_identity_removed
        ds.DeidentificationMethod = self.deidentification_method[:64]

    def _add_study_module(self, ds: Dataset):
        """Add Study Module attributes to dataset."""
        ds.StudyInstanceUID = self.study_instance_uid
        ds.StudyID = self.study_id
        ds.StudyDate = self.study_date
        ds.StudyTime = self.study_time
        ds.AccessionNumber = self.accession_number
        ds.ReferringPhysicianName = self.referring_physician_name[:64]

    def _add_series_module(self, ds: Dataset):
        """Add Series Module attributes to dataset."""
        ds.SeriesInstanceUID = self.series_instance_uid
        ds.SeriesNumber = self.series_number
        ds.Modality = self.modality.value

    def _add_instance_module(self, ds: Dataset):
        """Add Instance Module attributes to dataset."""
        ds.SOPInstanceUID = self.sop_instance_uid
        ds.SOPClassUID = self.sop_class_uid
        ds.InstanceNumber = self.instance_number

    def _add_device_module(self, ds: Dataset):
        """Add Secondary Capture Device Module attributes to dataset."""
        if self.secondary_capture_device_manufacturer:
            ds.SecondaryCaptureDeviceID = self.secondary_capture_device_id[:64]
            ds.SecondaryCaptureDeviceManufacturer = self.secondary_capture_device_manufacturer[
                :64]
            ds.SecondaryCaptureDeviceManufacturerModelName = \
                self.secondary_capture_device_manufacturer_model_name[:64]
            ds.SecondaryCaptureDeviceSoftwareVersions = \
                self.secondary_capture_device_software_versions[:64]

    def _add_image_module(self, ds: Dataset):
        """Add General Image Module attributes to dataset."""
        if self.image_comments:
            ds.ImageComments = self.image_comments
        if self.image_position_patient:
            ds.ImagePositionPatient = self.image_position_patient
        if self.image_orientation_patient:
            ds.ImageOrientationPatient = self.image_orientation_patient
        if self.patient_orientation:
            ds.PatientOrientation = self.patient_orientation


@dataclass
class RadiographMetadata(BaseDICOMMetadata):
    """
    Metadata for radiograph images (TIFF/PNG scanned radiographs).

    Extends BaseDICOMMetadata with radiograph-specific attributes.
    Corresponds to DICOM Secondary Capture Image IOD.

    Additional attributes:
        conversion_type → ConversionType (0008,0064)
        burned_in_annotation → BurnedInAnnotation (0028,0301)
        nominal_scanned_pixel_spacing → NominalScannedPixelSpacing (0018,2010)
        pixel_spacing → PixelSpacing (0028,0030)
        pixel_spacing_calibration_type → PixelSpacingCalibrationType (0028,0A02)
    """

    conversion_type: ConversionType = ConversionType.DF
    burned_in_annotation: BurnedInAnnotation = BurnedInAnnotation.YES
    nominal_scanned_pixel_spacing: Optional[List[str]] = None
    pixel_spacing: Optional[List[str]] = None
    pixel_spacing_calibration_type: str = "GEOMETRY"
    image_laterality: str = "U"  # Unknown by default

    def __post_init__(self):
        """Set radiograph-specific defaults."""
        super().__post_init__()
        # Default modality for radiographs
        if self.modality == ModalityType.OT:
            self.modality = ModalityType.RG

    def _add_image_module(self, ds: Dataset):
        """Add radiograph-specific image attributes."""
        super()._add_image_module(ds)

        ds.ConversionType = self.conversion_type.value
        ds.BurnedInAnnotation = self.burned_in_annotation.value

        if self.nominal_scanned_pixel_spacing:
            ds.NominalScannedPixelSpacing = self.nominal_scanned_pixel_spacing

        if self.pixel_spacing:
            ds.PixelSpacing = self.pixel_spacing
            ds.PixelSpacingCalibrationType = self.pixel_spacing_calibration_type

        if self.image_laterality:
            ds.ImageLaterality = self.image_laterality


@dataclass
class SurfaceMetadata(BaseDICOMMetadata):
    """
    Metadata for 3D surface models (STL files).

    Extends BaseDICOMMetadata for DICOM Encapsulated STL or
    Surface Segmentation Storage.

    Additional attributes for surface-specific information.
    """

    surface_processing_description: str = ""
    surface_processing_algorithm: str = ""

    def __post_init__(self):
        """Set surface-specific defaults."""
        super().__post_init__()
        # Will need specific SOP Class for STL
        # self.sop_class_uid = EncapsulatedSTLStorage


@dataclass
class DocumentMetadata(BaseDICOMMetadata):
    """
    Metadata for document files (PDF).

    Extends BaseDICOMMetadata for DICOM Encapsulated PDF Storage.

    Additional attributes:
        document_title → DocumentTitle (0042,0010)
        mime_type → MIMETypeOfEncapsulatedDocument (0042,0012)
    """

    document_title: str = ""
    mime_type: str = "application/pdf"

    def __post_init__(self):
        """Set document-specific defaults."""
        super().__post_init__()
        self.modality = ModalityType.DOC
        # Will need specific SOP Class for PDF
        # from pydicom.uid import EncapsulatedPDFStorage
        # self.sop_class_uid = EncapsulatedPDFStorage


@dataclass
class PhotographMetadata(BaseDICOMMetadata):
    """
    Metadata for visible light photographs (JPEG/PNG).

    Extends BaseDICOMMetadata for DICOM Visible Light Photographic Image.
    """

    def __post_init__(self):
        """Set photograph-specific defaults."""
        super().__post_init__()
        self.modality = ModalityType.XC
        # Will need specific SOP Class for VL Photography
        # from pydicom.uid import VLPhotographicImageStorage
        # self.sop_class_uid = VLPhotographicImageStorage
