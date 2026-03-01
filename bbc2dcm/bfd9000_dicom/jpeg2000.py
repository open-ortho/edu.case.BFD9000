import imagecodecs
from pydicom.encaps import encapsulate
from bfd9000_dicom import InvalidJPEG2000CodestreamError


def get_encapsulated_jpeg2k_pixel_data(img_array):
    jp2 = imagecodecs.jpeg2k_encode(img_array, level=0)
    codestream = get_codestream(jp2)
    if not is_valid_jpeg2000_codestream(codestream):
        raise InvalidJPEG2000CodestreamError(path="unknown")

    return encapsulate([codestream])


def is_valid_jpeg2000_codestream(byte_array):
    """
    Check if a byte array is a valid JPEG 2000 codestream.

    Parameters:
    byte_array (bytes): Byte array of the codestream.

    Returns:
    bool: True if it's a valid JPEG 2000 codestream, False otherwise.
    """
    # JPEG 2000 codestream starts with 0xFF4F (SOC marker) and ends with 0xFFD9 (EOC marker)
    soc_marker = b'\xFF\x4F'
    eoc_marker = b'\xFF\xD9'

    # Check if it starts with SOC marker and ends with EOC marker
    if byte_array.startswith(soc_marker) and byte_array.endswith(eoc_marker):
        return True
    else:
        return False


def get_codestream(encoded):
    """
    Extracts the JPEG 2000 codestream from a JP2 file format.

    Parameters:
    encoded (bytes): The JP2 encoded data.

    Returns:
    bytes: The raw JPEG 2000 codestream.
    """
    # JP2 codestream starts with the signature: 0xFF4F
    codestream_start_signature = b'\xFF\x4F'

    # We will scan the encoded bytes to find the start of the codestream
    codestream_start = encoded.find(codestream_start_signature)

    if codestream_start == -1:
        raise ValueError(
            "Codestream start signature not found in the encoded data.")

    # Now find the end of the codestream, which usually ends with 0xFFD9 (EOI marker)
    codestream_end_signature = b'\xFF\xD9'
    codestream_end = encoded.find(codestream_end_signature, codestream_start)

    if codestream_end == -1:
        raise ValueError(
            "Codestream end signature not found in the encoded data.")

    # Include the codestream end marker in the result
    codestream_end += len(codestream_end_signature)

    # Extract and return the codestream
    return encoded[codestream_start:codestream_end]
