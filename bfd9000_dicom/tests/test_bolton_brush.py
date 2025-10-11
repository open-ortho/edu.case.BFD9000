"""Tests for Bolton Brush utilities and RadiographMetadata features."""
import unittest
from bfd9000_dicom.extractors import extract_metadata_from_filename
from bfd9000_dicom.models import RadiographMetadata, PatientSex


class TestBoltonBrushUtilities(unittest.TestCase):
    """Test Bolton Brush specific utility functions."""

    def test_extract_bolton_brush_data_from_filename_basic(self):
        """Test basic Bolton Brush filename parsing."""
        result = extract_metadata_from_filename("B00131M020y05m.tiff")

        self.assertEqual(result.patient_id, "B0013")
        self.assertEqual(result.patient_sex, "M")
        self.assertEqual(result.patient_age, "245M")  # 20*12 + 5 = 245 months
        self.assertEqual(result.image_type, "1")

    def test_extract_bolton_brush_data_from_filename_female(self):
        """Test filename parsing for female patient."""
        result = extract_metadata_from_filename("B00202F015y08m.jpg")

        self.assertEqual(result.patient_id, "B0020")
        self.assertEqual(result.patient_sex, "F")
        self.assertEqual(result.patient_age, "188M")  # 15*12 + 8 = 188 months
        self.assertEqual(result.image_type, "2")

    def test_extract_bolton_brush_data_from_filename_edge_cases(self):
        """Test filename parsing edge cases."""
        # Minimum age (0 years, 1 month)
        result = extract_metadata_from_filename("B00011M000y01m.png")
        self.assertEqual(result.patient_id, "B0001")
        self.assertEqual(result.patient_sex, "M")
        self.assertEqual(result.patient_age, "001M")  # 0*12 + 1 = 1 month
        self.assertEqual(result.image_type, "1")

        # Maximum reasonable age
        result = extract_metadata_from_filename("B99992F050y11m.pdf")
        self.assertEqual(result.patient_id, "B9999")
        self.assertEqual(result.patient_sex, "F")
        self.assertEqual(result.patient_age, "611M")  # 50*12 + 11 = 611 months
        self.assertEqual(result.image_type, "2")


class TestRadiographMetadataBoltonBrush(unittest.TestCase):
    """Test Bolton Brush specific features in RadiographMetadata."""

    def test_bolton_brush_defaults_disabled(self):
        """Test that Bolton Brush defaults are not set when disabled."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M",
            is_bolton_brush_study=False
        )

        # Should not have Bolton Brush defaults
        self.assertNotEqual(metadata.patient_name,
                            "B0013^Bolton Study Subject")
        self.assertNotEqual(metadata.referring_physician_name,
                            "Broadbent^Birdsall^Holly^Dr.^Sr.")

    def test_bolton_brush_defaults_enabled(self):
        """Test that Bolton Brush defaults are set when enabled."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M",
            is_bolton_brush_study=True
        )

        # Should have Bolton Brush defaults
        self.assertEqual(metadata.patient_name, "B0013^Bolton Study Subject")
        self.assertEqual(metadata.referring_physician_name,
                         "Broadbent^Birdsall^Holly^Dr.^Sr.")
        self.assertEqual(metadata.secondary_capture_device_id, "Vidar")
        self.assertEqual(
            metadata.secondary_capture_device_manufacturer, "Vidar")
        self.assertEqual(
            metadata.secondary_capture_device_manufacturer_model_name, "DosimetryPRO Advantage")
        self.assertEqual(
            metadata.secondary_capture_device_software_versions, "49.7")
        self.assertEqual(metadata.conversion_type.value,
                         "DF")  # Digitized Film
        self.assertEqual(metadata.burned_in_annotation.value, "YES")

    def test_orientation_methods(self):
        """Test orientation setting methods."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M"
        )

        # Test LL orientation
        metadata.set_orientation_ll()
        self.assertEqual(metadata.patient_orientation, "LL")
        self.assertEqual(metadata.image_position_patient, "")
        self.assertEqual(metadata.image_orientation_patient, "")

        # Test PA orientation
        metadata.set_orientation_pa()
        self.assertEqual(metadata.patient_orientation, "PA")

        # Test HAND orientation
        metadata.set_orientation_hand()
        self.assertEqual(metadata.patient_orientation, "HAND")

    def test_to_dataset_includes_bolton_brush_tags(self):
        """Test that to_dataset includes Bolton Brush specific tags."""
        metadata = RadiographMetadata(
            patient_id="B0013",
            patient_sex=PatientSex.M,
            patient_age="217M",
            is_bolton_brush_study=True
        )

        ds = metadata.to_dataset()

        # Check that Bolton Brush tags are set
        self.assertEqual(ds.PatientName, "B0013^Bolton Study Subject")
        self.assertEqual(ds.ReferringPhysicianName,
                         "Broadbent^Birdsall^Holly^Dr.^Sr.")
        self.assertEqual(ds.SecondaryCaptureDeviceManufacturer, "Vidar")
        self.assertEqual(
            ds.SecondaryCaptureDeviceManufacturerModelName, "DosimetryPRO Advantage")
        self.assertEqual(ds.SecondaryCaptureDeviceSoftwareVersions, "49.7")
        self.assertEqual(ds.Modality, "RG")  # Radiographic imaging
        self.assertEqual(ds.ConversionType, "DF")  # Digitized Film
        self.assertEqual(ds.BurnedInAnnotation, "YES")


if __name__ == '__main__':
    unittest.main()
