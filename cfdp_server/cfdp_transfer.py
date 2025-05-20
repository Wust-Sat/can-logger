import pathlib
from spacepackets.cfdp.conf import ByteFieldU8
from spacepackets.cfdp import (
    PduConfig,
    TransmissionMode,
    ChecksumType,
)
from spacepackets.cfdp.pdu import (
    MetadataPdu,
    FileDataPdu,
    EofPdu,
    MetadataParams,
    FileDataParams,
)
from spacepackets.cfdp.defs import ConditionCode, ChecksumType
from cfdp_server.checksum import calculate_cfdp_modular_checksum

# 1. Configuration
SOURCE_ENTITY_ID_BYTES = b"\x00\x01"  # Example Source ID 1
DESTINATION_ENTITY_ID_BYTES = b"\x00\x02"  # Example Destination ID 2
TRANSACTION_SEQ_NUM_BYTES = b"\x00\x00\x00\x01"  # Example Transaction Sequence Number 1
SOURCE_FILE = pathlib.Path("/tmp/src-file.txt")
DESTINATION_FILE = pathlib.Path("dupa.txt")
FILE_SEGMENT_SIZE = 256 - 12
TRANSMISSION_MODE = TransmissionMode.UNACKNOWLEDGED


# Ensure the source file exists
if not SOURCE_FILE.exists():
    # Create a dummy file if it doesn't exist
    print(f"Source file {SOURCE_FILE} not found. Creating a dummy file.")
    with open(SOURCE_FILE, "w") as f:
        f.write("This is the content of the test file.\n")
        f.write("It has multiple lines.\n")
        f.write("CFDP will transfer this content segment by segment.\n")
        for i in range(10):
            f.write(f"Line {i+4} with some more data to make it larger.\n")

# 2. File Handling and Checksum Calculation
file_size = SOURCE_FILE.stat().st_size
print(f"Source File: {SOURCE_FILE}")
print(f"Destination File: {DESTINATION_FILE}")
print(f"File Size: {file_size} bytes")
print(f"Segment Size: {FILE_SEGMENT_SIZE} bytes")

# Calculate Checksum (Modular - Type 0)
print("Calculating checksum...")
checksum = calculate_cfdp_modular_checksum(SOURCE_FILE)
print(f"Modular Checksum (int): {checksum}")
print(f"Modular Checksum (hex): {checksum:08x}")

SequenceNumber = ByteFieldU8
EntityId = ByteFieldU8

# 3. PDU Configuration Setup
pdu_conf = PduConfig(
    source_entity_id=EntityId(SOURCE_ENTITY_ID_BYTES),
    dest_entity_id=EntityId(DESTINATION_ENTITY_ID_BYTES),
    transaction_seq_num=SequenceNumber(TRANSACTION_SEQ_NUM_BYTES),
    trans_mode=TRANSMISSION_MODE,
    # Other fields like CRC flag, segment metadata flag, etc., default to False/0
)

generated_pdus = []

# 4. Generate Metadata PDU
print("\nGenerating Metadata PDU...")
metadata_params = MetadataParams(
    closure_requested=False,  # No closure request in unacknowledged mode
    checksum_type=ChecksumType.MODULAR,
    file_size=file_size,
    source_file_name=str(SOURCE_FILE),  # Send only the name usually
    dest_file_name=str("dupa.txt"),
    # options=None # No TLV options for this basic example
)
metadata_pdu = MetadataPdu(pdu_conf=pdu_conf, params=metadata_params)
metadata_pdu_packed = metadata_pdu.pack()
generated_pdus.append(("Metadata", metadata_pdu_packed))
print(
    f"Metadata PDU Packed ({len(metadata_pdu_packed)} bytes):"
    f" {metadata_pdu_packed.hex()}"
)

# 5. Generate File Data PDUs
print("\nGenerating File Data PDUs...")
offset = 0
segment_count = 0
try:
    with open(SOURCE_FILE, "rb") as file:
        while True:
            file_segment = file.read(FILE_SEGMENT_SIZE)
            if not file_segment:
                break  # End of file

            params = FileDataParams(
                file_data=file_segment,
                offset=offset,
            )
            file_data_pdu = FileDataPdu(
                pdu_conf=pdu_conf,
                params=params,
                # segment_metadata_flag=False # Default
            )
            file_data_pdu_packed = file_data_pdu.pack()
            segment_count += 1
            generated_pdus.append((f"FileData_{segment_count}", file_data_pdu_packed))
            print(
                f"File Data PDU {segment_count} (Offset: {offset},"
                f" {len(file_data_pdu_packed)} bytes): {file_data_pdu_packed.hex()}"
            )

            offset += len(file_segment)

except IOError as e:
    print(f"Error reading file {SOURCE_FILE}: {e}")
    exit(1)

print(f"\nGenerated {segment_count} File Data PDUs.")

# 6. Generate EOF PDU
print("\nGenerating EOF PDU...")
eof_pdu = EofPdu(
    pdu_conf=pdu_conf,
    file_checksum=checksum.to_bytes(4, byteorder="big"),  # Checksum is 4 bytes
    file_size=file_size,
    condition_code=ConditionCode.NO_ERROR,
)
eof_pdu_packed = eof_pdu.pack()
generated_pdus.append(("EOF", eof_pdu_packed))
print(f"EOF PDU Packed ({len(eof_pdu_packed)} bytes): {eof_pdu_packed.hex()}")

print(f"\nTotal PDUs generated: {len(generated_pdus)}")

# You can now take the byte arrays in `generated_pdus`
# (e.g., metadata_pdu_packed, file_data_pdu_packed, eof_pdu_packed)
# and encapsulate them into your CAN-FD frames for transmission.
