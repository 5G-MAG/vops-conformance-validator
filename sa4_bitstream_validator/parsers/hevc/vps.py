"""
    Parsing of HEVC VPS.
"""

from .ptl import parse_profile_tier_level
from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention

def parse_vps(payload_data):
    """Parse Video Parameter Set from payload bytes"""
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(payload_data)
        if not clean_data:
            return None

        reader = BitReader(clean_data)

        # Parse basic VPS parameters
        vps = {
            'vps_video_parameter_set_id': reader.read_ue(),
            'vps_base_layer_internal_flag': reader.read_bit(),
            'vps_base_layer_available_flag': reader.read_bit(),
            'vps_max_layers_minus1': reader.read_bits(6),
            'vps_max_sub_layers_minus1': reader.read_bits(3),
            'vps_temporal_id_nesting_flag': reader.read_bit(),
            'vps_reserved_0xffff_16bits': reader.read_bits(16)
        }
        vps = {**vps, **parse_profile_tier_level(True, vps["vps_max_sub_layers_minus1"], reader)}


        return {k: v for k, v in vps.items() if v is not None}

    except Exception as e:
        print(f"VPS parsing error: {str(e)}")
        return None
