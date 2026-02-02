"""
    Parsing of HEVC SEI messages.
"""

from bitstring import Error
from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention
from sa4_bitstream_validator.parsers.hevc.sei.three_dimensional_reference_displays import parse_three_dimensional_reference_displays_info


def parse_sei_rbsp(payload_data):
    """Parse SEI RBSP (Raw Byte Sequence Payload)"""
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(payload_data)
        if not clean_data:
            return None

        reader = BitReader(clean_data)
        sei_messages = []
        
        # Parse SEI messages until no more data
        while reader.remaining_bits() > 8:  # Need at least 8 bits for trailing bits
            sei_message = parse_sei_message(reader)
            if sei_message:
                sei_messages.append(sei_message)
            else:
                break
        
        # Parse RBSP trailing bits
        if reader.remaining_bits() >= 8:
            rbsp_trailing_bits(reader)
        
        return sei_messages
        
    except Error as e:
        print(f"SEI RBSP parsing error: {str(e)}")
        return None


def parse_sei_message(reader):
    """Parse a single SEI message"""
    try:
        sei_message = {}
        
        # Parse payload type
        payload_type = 0
        while reader.next_bits(8) == 0xFF:
            reader.read_bits(8)  # Skip ff_byte
            payload_type += 255
        
        last_payload_type_byte = reader.read_bits(8)
        payload_type += last_payload_type_byte
        sei_message["payload_type"] = payload_type
        
        # Parse payload size
        payload_size = 0
        while reader.next_bits(8) == 0xFF:
            reader.read_bits(8)  # Skip ff_byte
            payload_size += 255
        
        last_payload_size_byte = reader.read_bits(8)
        payload_size += last_payload_size_byte
        sei_message["payload_size"] = payload_size
        
        # Parse payload based on type
        sei_message["payload"] = parse_sei_payload(payload_type, payload_size, reader)
        
        # Parse payload extension if present
        if reader.remaining_bits() > 0:
            if more_data_in_payload(reader):
                if payload_extension_present(reader):
                    # Skip reserved payload extension data
                    while reader.remaining_bits() > 0:
                        reader.read_bit()
                
                # Parse payload trailing bits
                payload_bit_equal_to_one = reader.read_bit()
                if payload_bit_equal_to_one != 1:
                    print("Warning: payload_bit_equal_to_one is not 1")
                
                # Skip remaining bits until byte-aligned
                while not reader.is_byte_aligned():
                    payload_bit_equal_to_zero = reader.read_bit()
                    if payload_bit_equal_to_zero != 0:
                        print("Warning: payload_bit_equal_to_zero is not 0")
        
        return sei_message
        
    except Error as e:
        print(f"SEI message parsing error: {str(e)}")
        return None


def parse_sei_payload(payload_type, payload_size, reader):
    """Parse SEI payload based on payload type"""
    # Save current position to calculate bytes read
    start_pos = reader.get_position()

    try:
        # Handle different payload types
        if payload_type == 176:  # three_dimensional_reference_displays_info
            return parse_three_dimensional_reference_displays_info(payload_size, reader)
        else:
            # For unsupported payload types, skip the payload bytes
            bytes_to_skip = payload_size
            while bytes_to_skip > 0:
                reader.read_bits(8)
                bytes_to_skip -= 1
            return {"type": "unsupported", "payload_type": payload_type}

    except Error as e:
        print(f"SEI payload parsing error for type {payload_type}: {str(e)}")
        # Skip remaining bytes if there was an error
        current_pos = reader.get_position()
        bytes_read = (current_pos - start_pos) // 8
        bytes_remaining = payload_size - bytes_read

        while bytes_remaining > 0:
            reader.read_bits(8)
            bytes_remaining -= 1

        return {"type": "error", "payload_type": payload_type, "error": str(e)}



def more_data_in_payload(reader):
    """Check if there's more data in the payload"""
    return reader.remaining_bits() > 0


def payload_extension_present(reader):
    """Check if payload extension is present"""
    # This would need to be determined based on the specific SEI message
    # For now, return False as we're not implementing full extension support
    return False


def rbsp_trailing_bits(reader):
    """Parse RBSP trailing bits"""
    # Read rbsp_trailing_bits (should be 1 followed by zeros until byte-aligned)
    rbsp_stop_one_bit = reader.read_bit()
    if rbsp_stop_one_bit != 1:
        print("Warning: rbsp_stop_one_bit is not 1")
    
    # Skip zeros until byte-aligned
    while not reader.is_byte_aligned():
        rbsp_alignment_zero_bit = reader.read_bit()
        if rbsp_alignment_zero_bit != 0:
            print("Warning: rbsp_alignment_zero_bit is not 0")