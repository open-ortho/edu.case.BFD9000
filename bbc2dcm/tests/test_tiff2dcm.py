import unittest
from bfd9000_dicom.tiff2dcm import extract_and_convert_data, build_dicom_without_image, load_dataset_from_file
import logging
import json

DCMJSONFILE = './test.dcm.json'

class TestTiff2Dicom(unittest.TestCase):

    file_path = "./Downloads/B0013LM18y01m.tif"

    def test_extract_data_from_filename(self):

        a, b, c, d = extract_and_convert_data(self.file_path)
        self.assertEqual(a,"B0013")
        self.assertEqual(b,"L")
        self.assertEqual(c,"M")
        self.assertEqual(d,"217M")

    @unittest.skip
    def test_build_dicom(self):
        ds = build_dicom_without_image(self.file_path)
        with open('./test.dcm.json','w') as json_file:
            json.dump(ds.to_json_dict(),json_file,indent=4)

    def test_load_dataset_from_json(self):
        ds = load_dataset_from_file(DCMJSONFILE)
        print(ds)