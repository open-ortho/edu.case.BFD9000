import unittest

from bfd9000_dicom.dicom_tags import dpi_to_dicom_spacing

class TestDicomTags(unittest.TestCase):

    def test_dpi_to_dicom_spacing(self):
        # Example usage:
        dpi_horiz = 300
        dpi_vert = 150
        spacing, aspect_ratio = dpi_to_dicom_spacing(dpi_horiz, dpi_vert)
        print("NominalScannedPixelSpacing:", spacing, "mm")
        print("PixelAspectRatio:", aspect_ratio)
        self.assertEqual(int(aspect_ratio[0])/int(aspect_ratio[1]),0.5)
        self.assertAlmostEqual(float(spacing[0]),0.0847, places=4)
        self.assertAlmostEqual(float(spacing[1]),0.1693, places=4)
        self.assertIsInstance(spacing,list)
        self.assertIsInstance(aspect_ratio,tuple)