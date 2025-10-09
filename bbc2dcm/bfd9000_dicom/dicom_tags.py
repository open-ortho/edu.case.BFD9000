""" DICOM tags for specific types of images.

A good explanation for ImageOrientationPatient
https://dicomiseasy.blogspot.com/2013/06/getting-oriented-using-image-plane.html
"""
from typing import Optional
import pydicom
from pydicom import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, JPEG2000Lossless
import numpy as np
from PIL import Image
from bfd9000_dicom.jpeg2000 import get_encapsulated_jpeg2k_pixel_data
from bfd9000_dicom import logger, UnsupportedBitDepthError, UnsupportedImageModeError

def dicom_tags_LL(ds: Dataset):
    ds.ImagePositionPatient = ''
    ds.ImageOrientationPatient = ''


def dicom_tags_PA(ds: Dataset):
    ds.ImagePositionPatient = ''
    ds.ImageOrientationPatient = ''


def dicom_tags_HAND(ds: Dataset):
    ds.ImagePositionPatient = ''
    ds.ImageOrientationPatient = ''



image_type_dispatcher = {
    "XV.CG.LL": dicom_tags_LL,
    "XV.CG.PA": dicom_tags_PA
}


def expected_tags():
    """ The set of expected tags to come in from JSON.

    These depend on the image, 

    """

    ds = Dataset()
    ds.DateOfSecondaryCapture = ''
    ds.TimeOfSecondaryCapture = ''
    ds.PatientAge = ''
    ds.PatientSex = ''
    ds.PatientId = ''
    ds.PatientOrientation = ''
    ds.AnatomicRegionSequence = []


def build_file_meta() -> FileMetaDataset:
    """ File Meta for Secondary Capture SC IOD. """
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.ImplementationClassUID = pydicom.uid.generate_uid()
    return file_meta

def add_common_bolton_brush_tags(ds:Dataset) -> Optional[Dataset]:
    """ Add tags which are common to all scanned bolton brush radiographs.
    """
    if ds is None:
        return None
    ds.PatientName = f'{ds.PatientID}^Bolton Study Subject'
    ds.ReferringPhysicianName = 'Broadbent^Birdsall^Holly^Dr.^Sr.'[:64]

    ds.SecondaryCaptureDeviceID = ''[:64]
    ds.SecondaryCaptureDeviceManufacturer = 'Vidar'[:64]
    ds.SecondaryCaptureDeviceManufacturerModelName = 'DosimetryPRO Advantage'[:64]
    ds.SecondaryCaptureDeviceSoftwareVersions = '49.7'[:64]

    ds.Modality = 'RG'  # Radiographic imaging (conventional film/screen)
    ds.ConversionType = 'DF'  # Digitized Film

    # Patient Module
    ds.PatientBirthDate = '' # Required, must stay empty
    ds.PatientIdentityRemoved = 'YES'
    ds.DeidentificationMethod = 'Removed: Patient name, birthdate, study date/time.'[:64]

    # General Study Module
    ds.StudyDate = ""  # These are required or empty if unknown.
    ds.StudyTime = ""  # These are required or empty if unknown.

    # General Image Module
    ds.BurnedInAnnotation = 'YES'  # do all of the cephs have it?


def add_image_module(ds:Dataset,tiff_path,with_compression=True):
    """ Adds the DICOM Image Module. """
    try:
        with Image.open(tiff_path) as img:
            img.seek(0)
            # Extract DPI information
            dpi_horizontal, dpi_vertical = img.info['dpi']
            mode = img.mode
            if mode in ['RGBA','P']:
                img = img.convert('RGB')
            elif mode == 'LA':
                img = img.convert('L')
            elif mode not in ['L', 'RGB', 'I;16']:
                raise UnsupportedImageModeError(mode)

            if with_compression:
                img_array = np.array(img)
            else:
                # Load the image into a numpy array and ensure it's in 16-bit
                # Explicitly setting dtype to uint16
                img_array = np.array(img, dtype=np.uint16)

            if img_array.dtype == np.uint8:
                bits_allocated = 8
            elif img_array.dtype == np.uint16:
                bits_allocated = 16
            else:
                raise UnsupportedBitDepthError(img_array.dtype)

            ds.Rows, ds.Columns = img_array.shape[0], img_array.shape[1]
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.PixelRepresentation = 0
            ds.BitsStored = bits_allocated
            ds.BitsAllocated = bits_allocated
            ds.HighBit = ds.BitsStored - 1

            (ds.NominalScannedPixelSpacing, ds.PixelAspectRatio) = dpi_to_dicom_spacing(
                dpi_horizontal, dpi_vertical)
            ds.PixelSpacing = ds.NominalScannedPixelSpacing
            ds.PixelSpacingCalibrationType = "GEOMETRY"

            if with_compression:
                ds.file_meta.TransferSyntaxUID = JPEG2000Lossless
                ds.PixelData = get_encapsulated_jpeg2k_pixel_data(img_array)
            else:
                ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
                ds.PixelData = img_array.tobytes()
            add_common_bolton_brush_tags(ds)
            return ds

    except Exception as e:
        logger.error(f"Error processing image {tiff_path}: {e}")
        return None


def dpi_to_dicom_spacing(dpi_horizontal, dpi_vertical=None):
    """
    Convert DPI to DICOM's NominalScannedPixelSpacing and PixelAspectRatio.

    Parameters:
    dpi_horizontal (float): The DPI for the horizontal dimension.
    dpi_vertical (float, optional): The DPI for the vertical dimension. If not provided,
        it is assumed that vertical DPI is the same as horizontal DPI.

    Returns:
    tuple: Returns two tuples:
        - NominalScannedPixelSpacing: Tuple of two floats (spacingX, spacingY) in mm.
        - PixelAspectRatio: Tuple of two integers (aspectX, aspectY) or None if pixels are square.
    """
    mm_per_inch = 25.4  # 1 inch is 25.4 millimeters

    if dpi_vertical is None:
        dpi_vertical = dpi_horizontal

    # Calculate pixels per millimeter
    ppmm_horizontal = dpi_horizontal / mm_per_inch
    ppmm_vertical = dpi_vertical / mm_per_inch

    # Calculate NominalScannedPixelSpacing in mm
    spacing_horizontal = 1 / ppmm_horizontal
    spacing_vertical = 1 / ppmm_vertical

    # Calculate PixelAspectRatio using original dpi values to avoid rounding errors
    if dpi_horizontal == dpi_vertical:
        pixel_aspect_ratio = [1, 1]
    else:
        # Reduce aspect ratio to simplest form
        from math import gcd
        gcd_ratio = gcd(int(dpi_vertical), int(dpi_horizontal))
        pixel_aspect_ratio = [
            f"{int(dpi_vertical / gcd_ratio)}", f"{int(dpi_horizontal / gcd_ratio)}"]

    return ([f"{spacing_horizontal}", f"{spacing_vertical}"], pixel_aspect_ratio)
