"""
    Parsing of HEVC profile, tier and level structure.
"""

def parse_profile_tier_level(profile_present_flag: bool, max_num_sub_layers_minus1: int, reader):
    """Parse profile tier level strucuture in the current bitstream"""
    ptl = {}
    if profile_present_flag:
        profile = {
            "general_profile_space": reader.read_bits(2),
            "general_tier_flag": reader.read_bit(),
            "general_profile_idc": reader.read_bits(5),
            "general_profile_compatibility_flag": reader.read_flags(32),
            "general_progressive_source_flag": reader.read_bit(),
            "general_interlaced_source_flag": reader.read_bit(),
            "general_non_packed_constraint_flag": reader.read_bit(),
            "general_fame_only_constraint_flag": reader.read_bit(),
        }
        if any(profile["general_profile_idc"] == i or profile["general_profile_compatibility_flag"][i] for i in range(4, 12)):
            profile = {
                    **profile,
                    **{
                        "general_max_12bit_constraint_flag": reader.read_bit(),
                        "general_max_10bit_constraint_flag": reader.read_bit(),
                        "general_max_8bit_constraint_flag": reader.read_bit(),
                        "general_max_422chroma_constraint_flag": reader.read_bit(),
                        "general_max_420chroma_constraint_flag": reader.read_bit(),
                        "general_max_monochrome_constraint_flag": reader.read_bit(),
                        "general_intra_constraint_flag": reader.read_bit(),
                        "general_one_picture_only_constraint_flag": reader.read_bit(),
                        "general_lower_bit_rate_constraint_flag": reader.read_bit(),
                    }
            }
            if any(profile["general_profile_idc"] == i or profile["general_profile_compatibility_flag"][i] for i in [5, 9, 10, 11]):
                profile = {
                        **profile,
                        **{
                            "general_max_14bit_constraint_flag": reader.read_bit(),
                            "general_reserved_zero_33bits": reader.read_bits(33),
                        }
                }
            else:
                profile = {
                        **profile,
                        **{
                            "general_reserved_zero_34bits": reader.read_bits(34),
                        }
                }
        elif profile["general_profile_idc"] == 2 or profile["general_profile_compatibility_flag"][2]:
            profile = {
                    **profile,
                    **{
                        "general_reserved_zero_7bits": reader.read_bits(7),
                        "general_one_picture_only_constraint_flag": reader.read_bit(),
                        "general_reserved_zero_35bits": reader.read_bits(35),
                    }
            }
        else:
            profile = {
                    **profile,
                    **{
                        "general_reserved_zero_43bits": reader.read_bits(43),
                    }
            }

        if any(profile["general_profile_idc"] == i or profile["general_profile_compatibility_flag"][i] for i in [1, 2, 3, 4, 5, 9, 11]):
            profile = {
                    **profile,
                    **{
                        "general_inbld_flag": reader.read_bit(),
                    }
            }
        else:
            profile = {
                    **profile,
                    **{
                        "general_reserved_zero_bit": reader.read_bit(),
                    }
            }
        # End of profile parameters
        ptl = {**ptl, **profile}

        level = {
            "general_level_idc": reader.read_bits(8),
        }
        for i in range(max_num_sub_layers_minus1):
            level = {
                **level,
                **{
                    f"sub_layer_profile_present_flag[{i}]": reader.read_bit(),
                    f"sub_layer_level_present_flag[{i}]": reader.read_bit(),
                }
            }
        if max_num_sub_layers_minus1 > 0:
            for i in range(max_num_sub_layers_minus1, 8):
                level = {
                    **level,
                    **{
                        f"reserved_zero_2bits[{i}]": reader.read_bits(2),
                   }
                }
        for i in range(max_num_sub_layers_minus1-6):
            if level[f"sub_layer_profile_present_flag[{i}]"]:
                level = {
                    **level,
                    **{
                        f"sub_layer_profile_space[{i}]": reader.read_bits(2),
                        f"sub_layer_tier_flag[{i}]": reader.read_bit(),
                        f"sub_layer_profile_idc[{i}]": reader.read_bits(5),
                        f"sub_layer_profile_compatibility_flag[{i}]": reader.read_flags(32),
                        f"sub_layer_progressive_source_flag[{i}]": reader.read_bit(),
                        f"sub_layer_interlaced_source_flag[{i}]": reader.read_bit(),
                        f"sub_layer_non_packed_constraint_flag[{i}]": reader.read_bit(),
                        f"sub_layer_frame_only_constraint_flag[{i}]": reader.read_bit(),
                   }
                }
                #TODO: Check from there, this seems where it deviates
                if any(level[f"sub_layer_profile_idc[{i}]"] == j or level[f"sub_layer_profile_compatibility_flag[{i}]"][j] for j in range(4,12)):
                    level = {
                        **level,
                        **{
                            f"sub_layer_max_12bit_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_max_10bit_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_max_8bit_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_max_422chroma_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_max_420chroma_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_max_monochrome_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_intra_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_one_picture_only_constraint_flag[{i}]": reader.read_bit(),
                            f"sub_layer_lower_bit_rate_constraint_flag[{i}]": reader.read_bit(),
                       }
                    }
                else:
                    level = {
                        **level,
                        **{
                            f"sub_layer_reserved_zero_43bits[{i}]": reader.read_bits(43),
                       }
                    }


        # End of level parameters
        ptl = {**ptl, **level}

    return ptl
