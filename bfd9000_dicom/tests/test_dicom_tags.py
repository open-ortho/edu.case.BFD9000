"""Tests for DICOM metadata models and utilities."""
import unittest
from bfd9000_dicom.models import (
    RadiographMetadata,
    PatientSex,
    ModalityType,
    ConversionType,
    BurnedInAnnotation,
)
from bfd9000_dicom.core.dicom_builder import dpi_to_dicom_spacing


class TestDICOMMetadata(unittest.TestCase):
    """Test DICOM metadata model functionality."""

    def test_radiograph_metadata_creation(self):
        """Test basic RadiographMetadata creation."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M"
        )
        
        self.assertEqual(metadata.patient_id, "B0013")
        self.assertEqual(metadata.patient_sex, PatientSex.M)
        self.assertEqual(metadata.patient_age, "217M")
        self.assertEqual(metadata.modality, ModalityType.RG)

    def test_radiograph_metadata_to_dataset(self):
        """Test conversion of RadiographMetadata to DICOM dataset."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.F,
            patient_age="180M",
            patient_name="Smith^Jane",
            study_instance_uid="1.2.3.4.5",
            series_instance_uid="1.2.3.4.6",
            instance_number="1"
        )
        
        ds = metadata.to_dataset()
        
        # Check patient module
        self.assertEqual(ds.PatientID, "B0013")
        self.assertEqual(ds.PatientSex, "F")
        self.assertEqual(ds.PatientAge, "180M")
        self.assertEqual(ds.PatientName, "Smith^Jane")
        
        # Check study module
        self.assertEqual(ds.StudyInstanceUID, "1.2.3.4.5")
        self.assertEqual(ds.SeriesInstanceUID, "1.2.3.4.6")
        self.assertEqual(ds.InstanceNumber, "1")
        
        # Check modality
        self.assertEqual(ds.Modality, "RG")

    def test_radiograph_metadata_with_pixel_spacing(self):
        """Test RadiographMetadata with pixel spacing attributes."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M",
            pixel_spacing=["0.1", "0.1"],
            nominal_scanned_pixel_spacing=["0.1", "0.1"],
            pixel_spacing_calibration_type="GEOMETRY"
        )
        
        ds = metadata.to_dataset()
        
        self.assertEqual(ds.PixelSpacing, ["0.1", "0.1"])
        self.assertEqual(ds.NominalScannedPixelSpacing, ["0.1", "0.1"])
        self.assertEqual(ds.PixelSpacingCalibrationType, "GEOMETRY")

    def test_radiograph_metadata_bolton_brush_features(self):
        """Test Bolton Brush specific features in RadiographMetadata."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M",
            is_bolton_brush_study=True
        )
        
        # Check Bolton Brush defaults are applied
        self.assertEqual(metadata.patient_name, "B0013^Bolton Study Subject")
        self.assertEqual(metadata.referring_physician_name, "Broadbent^Birdsall^Holly^Dr.^Sr.")
        self.assertEqual(metadata.conversion_type, ConversionType.DF)
        self.assertEqual(metadata.burned_in_annotation, BurnedInAnnotation.YES)
        
        # Check dataset conversion
        ds = metadata.to_dataset()
        self.assertEqual(ds.ConversionType, "DF")
        self.assertEqual(ds.BurnedInAnnotation, "YES")
        self.assertEqual(ds.SecondaryCaptureDeviceManufacturer, "Vidar")

    def test_radiograph_metadata_orientation_methods(self):
        """Test orientation setting methods."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M"
        )
        
        # Test each orientation
        metadata.set_orientation_ll()
        self.assertEqual(metadata.patient_orientation, "LL")
        
        metadata.set_orientation_pa()
        self.assertEqual(metadata.patient_orientation, "PA")
        
        metadata.set_orientation_hand()
        self.assertEqual(metadata.patient_orientation, "HAND")

    def test_dpi_to_dicom_spacing(self):
        """Test DPI to DICOM pixel spacing conversion."""
        # Test square pixels
        spacing, aspect_ratio = dpi_to_dicom_spacing(300, 300)
        self.assertAlmostEqual(float(spacing[0]), 0.0847, places=4)
        self.assertAlmostEqual(float(spacing[1]), 0.0847, places=4)
        self.assertEqual(aspect_ratio, ["1", "1"])
        
        # Test rectangular pixels
        spacing, aspect_ratio = dpi_to_dicom_spacing(300, 150)
        self.assertAlmostEqual(float(spacing[0]), 0.0847, places=4)
        self.assertAlmostEqual(float(spacing[1]), 0.1693, places=4)
        self.assertEqual(aspect_ratio, ["1", "2"])
        
        # Test with None vertical DPI (defaults to horizontal)
        spacing, aspect_ratio = dpi_to_dicom_spacing(300, None)
        self.assertAlmostEqual(float(spacing[0]), 0.0847, places=4)
        self.assertAlmostEqual(float(spacing[1]), 0.0847, places=4)
        self.assertEqual(aspect_ratio, ["1", "1"])


class TestDICOMEnums(unittest.TestCase):
    """Test DICOM enumeration values."""

    def test_patient_sex_enum(self):
        """Test PatientSex enum values."""
        self.assertEqual(PatientSex.M.value, "M")
        self.assertEqual(PatientSex.F.value, "F")
        self.assertEqual(PatientSex.O.value, "O")
        self.assertEqual(PatientSex.U.value, "U")

    def test_modality_type_enum(self):
        """Test ModalityType enum values."""
        self.assertEqual(ModalityType.STUDYMODEL.value, "M3D")
        self.assertEqual(ModalityType.CEPHALOGRAM.value, "RG")
        self.assertEqual(ModalityType.DX.value, "DX")
        self.assertEqual(ModalityType.CR.value, "CR")
        self.assertEqual(ModalityType.DOC.value, "DOC")
        self.assertEqual(ModalityType.XC.value, "XC")

    def test_conversion_type_enum(self):
        """Test ConversionType enum values."""
        self.assertEqual(ConversionType.DF.value, "DF")
        self.assertEqual(ConversionType.SI.value, "SI")
        self.assertEqual(ConversionType.SYN.value, "SYN")

    def test_burned_in_annotation_enum(self):
        """Test BurnedInAnnotation enum values."""
        self.assertEqual(BurnedInAnnotation.YES.value, "YES")
        self.assertEqual(BurnedInAnnotation.NO.value, "NO")


if __name__ == '__main__':
    unittest.main()