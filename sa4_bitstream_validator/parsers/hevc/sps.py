"""
    Parsing of HEVC SPS.
"""

from .ptl import parse_profile_tier_level
from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention

def parse_sps(payload_data):
    """Parse Sequence Parameter Set from payload bytes"""
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(payload_data)
        if not clean_data:
            return None

        reader = BitReader(clean_data)

        # Parse basic SPS parameters
        sps = {
            "sps_video_parameter_set_id": reader.read_bits(4),
            "sps_max_sub_layers_minus1": reader.read_bits(3),
            "sps_temporal_id_nesting_flag": reader.read_bit(),
        }
        sps = {**sps, **parse_profile_tier_level(True, sps["sps_max_sub_layers_minus1"], reader)}

        return {k: v for k, v in sps.items() if v is not None}

    except Exception as e:
        print(f"SPS parsing error: {str(e)}")
        return None
