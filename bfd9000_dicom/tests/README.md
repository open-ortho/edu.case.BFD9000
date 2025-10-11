# Tests

This directory contains unit tests for the bfd9000_dicom package.

## Test Structure

- `test_converters.py` - Tests for the new router-based converter system
- `test_compression.py` - Tests for JPEG2000 compression utilities
- `test_dicom_tags.py` - Tests for DICOM metadata models and utilities
- `test_tiff2dcm.py` - Tests for TIFF converter and Bolton Brush utilities
- `test_bolton_brush.py` - Tests for Bolton Brush specific features and utilities
- `test_integration.py` - Integration tests for end-to-end converter workflows
- `test.dcm.json` - Sample DICOM metadata in JSON format for testing

## Test Categories

### Unit Tests
- **Converter Router**: File type detection and routing logic
- **Individual Converters**: TIFF, PNG, JPEG, PDF, STL converter functionality
- **Compression**: JPEG2000 encoding/decoding utilities
- **Metadata Models**: DICOM DTO creation and validation
- **Utilities**: Bolton Brush filename parsing and JSON loading

### Integration Tests
- **End-to-End Conversion**: Complete workflows from file to DICOM
- **Router Functionality**: Automatic converter selection and execution
- **Bolton Brush Workflows**: Complete Bolton Brush study conversion process

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
python -m pytest --cov=bfd9000_dicom tests/
```

## Test Data

- `test.dcm.json`: Sample DICOM dataset in JSON format for backward compatibility testing
- Mock files are used for converter tests to avoid dependencies on actual image files

## CI/CD

Tests are automatically run on:
- Pull requests to main branch
- Pushes to main branch
- Manual workflow dispatch

Coverage reports are generated and uploaded to Codecov.
