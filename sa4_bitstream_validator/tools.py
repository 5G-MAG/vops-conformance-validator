"""
    Generic functions usefull to parse NAL unit bitstreams.
"""

def remove_emulation_prevention(data):
    """Remove HEVC emulation prevention bytes (0x03 after 00 00)"""
    result = []
    i = 0
    while i < len(data):
        if i <= len(data) - 3 and data[i] == 0 and data[i+1] == 0 and data[i+2] == 0x03:
            result.extend([data[i], data[i+1]])
            i += 3
        else:
            result.append(data[i])
            i += 1
    return bytes(result)


def find_start_codes(data):
    """Locate all start codes (0x000001 and 0x00000001) in the bitstream"""
    start_codes = []
    i = 0
    while i <= len(data) - 4:
        # Check for 4-byte start code
        if data[i:i+4] == b'\x00\x00\x00\x01':
            start_codes.append((i, 4))
            i += 4
        # Check for 3-byte start code
        elif data[i:i+3] == b'\x00\x00\x01':
            start_codes.append((i, 3))
            i += 3
        else:
            i += 1
    return start_codes
