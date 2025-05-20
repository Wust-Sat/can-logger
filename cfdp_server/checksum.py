import pathlib
import struct  # Needed for packing bytes for checksum calculation


def calculate_cfdp_modular_checksum(file_path: pathlib.Path) -> int:
    """
    Calculates the CFDP modular checksum (Type 0) for a given file.

    Ref: CCSDS 727.0-B-5 Section 4.2.5

    Args:
        file_path: Path to the file.

    Returns:
        The calculated 32-bit checksum as an integer.
    """
    checksum = 0
    bytes_read_total = 0
    try:
        with open(file_path, "rb") as file:
            while True:
                # Read in chunks, process 4 bytes at a time
                chunk = file.read(4)
                bytes_read_total += len(chunk)

                if not chunk:
                    break  # End of file

                if len(chunk) == 4:
                    # Unpack 4 bytes into a big-endian unsigned integer
                    word = struct.unpack(">I", chunk)[0]
                    checksum += word
                else:
                    # Handle padding for the last partial chunk
                    padded_chunk = chunk + bytes(4 - len(chunk))  # Pad with \x00
                    word = struct.unpack(">I", padded_chunk)[0]
                    checksum += word
                    # Since this is the last chunk, break the loop
                    break

                # Apply modulo 2^32
                checksum &= 0xFFFFFFFF

    except IOError as e:
        print(f"Error reading file {file_path} for checksum: {e}")
        raise  # Re-raise the exception

    # Final modulo operation (though often redundant due to loop)
    return checksum & 0xFFFFFFFF
