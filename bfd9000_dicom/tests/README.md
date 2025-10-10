# Tests

This directory contains unit tests for the bfd9000_dicom package.

## Test Structure

- `test_converters.py` - Tests for converter classes (radiograph, surface, document, photograph)
- `test_compression.py` - Tests for JPEG2000 compression utilities
- `test_dicom_tags.py` - Tests for DICOM builder utilities (now in core module)
- `test_tiff2dcm.py` - Tests for radiograph converter (backward compatibility tests)
- `test.dcm.json` - Sample DICOM metadata in JSON format for testing

## Running Tests

To run all tests:

```bash
cd bfd9000_dicom
python -m pytest tests/
```

To run a specific test file:

```bash
python -m pytest tests/test_converters.py
```

To run with coverage:

```bash
python -m pytest tests/ --cov=bfd9000_dicom --cov-report=html
```

## Test Coverage

The tests cover:

1. **Converters**: Verify that each converter class exists and behaves correctly
   - RadiographConverter: Full implementation tests
   - SurfaceConverter, DocumentConverter, PhotographConverter: NotImplementedError tests

2. **Compression**: JPEG2000 compression and validation
   - Codestream validation
   - Codestream extraction from JP2 containers
   - Full compression pipeline

3. **DICOM Builder**: Core DICOM building utilities
   - DPI to pixel spacing conversion
   - File metadata creation
   - Tag addition

4. **Backward Compatibility**: Old API still works
   - Filename parsing
   - Dataset building
   - JSON loading
