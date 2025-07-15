"""
    Parsing of HEVC profile, tier and level structure.
"""

def parse_profile_tier_level(profile_present_flag: bool, max_num_sub_layers_minus1: int, reader):
    """Parse profile tier level strucuture in the current bitstream"""
    ptl = {}

    try:
        if profile_present_flag:
            reader.read_bits(96)
            level = {}
            for i in range(max_num_sub_layers_minus1):
                level[f"sub_layer_profile_present_flag[{i}]"] = reader.read_bit()
                level[f"sub_layer_level_present_flag[{i}]"] = reader.read_bit()
            if max_num_sub_layers_minus1 > 0:
                for i in range(max_num_sub_layers_minus1, 8):
                    reader.read_bits(2)
            for i in range(max_num_sub_layers_minus1-5):
                if i == 0:
                    if level[f"sub_layer_profile_present_flag[{i}]"]:
                        reader.read_bits(80)
                elif i==1:
                    pass
                else:
                    if level[f"sub_layer_profile_present_flag[{i}]"]:
                        reader.read_bits(88)
                    if level[f"sub_layer_level_present_flag[{i}]"]:
                        reader.read_bits(8)

            # End of level parameters
            ptl = {**ptl, **level}

    except Exception as e:
        print(f"PTL parsing error: {str(e)}")
        return None

    return ptl
