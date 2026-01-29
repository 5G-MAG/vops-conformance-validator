"""
    Parsing of HEVC profile, tier and level structure.
"""

from bitstring import Error

def parse_profile_tier_level(profile_present_flag: bool, max_num_sub_layers_minus1: int, reader):
    """Parse profile tier level strucuture in the current bitstream"""
    ptl = {}

    try:
        if profile_present_flag:
            # Parse profile/tier/level information
            ptl["general_profile_space"] = reader.read_bits(2)
            ptl["general_tier_flag"] = reader.read_bit()
            ptl["general_profile_idc"] = reader.read_bits(5)
            
            # Parse profile compatibility flags
            for j in range(32):
                ptl[f"general_profile_compatibility_flag[j={j}]"] = reader.read_bit()
            
            # Parse source and constraint flags
            ptl["general_progressive_source_flag"] = reader.read_bit()
            ptl["general_interlaced_source_flag"] = reader.read_bit()
            ptl["general_non_packed_constraint_flag"] = reader.read_bit()
            ptl["general_frame_only_constraint_flag"] = reader.read_bit()
            
            # Conditional parsing based on profile IDC and compatibility flags
            profile_idc = ptl["general_profile_idc"]
            compatibility_flags = [ptl[f"general_profile_compatibility_flag[j={j}]"] for j in range(32)]
            
            if (profile_idc == 4 or compatibility_flags[4] or 
                profile_idc == 5 or compatibility_flags[5] or
                profile_idc == 6 or compatibility_flags[6] or
                profile_idc == 7 or compatibility_flags[7] or
                profile_idc == 8 or compatibility_flags[8] or
                profile_idc == 9 or compatibility_flags[9] or
                profile_idc == 10 or compatibility_flags[10] or
                profile_idc == 11 or compatibility_flags[11]):
                
                # Parse extended constraint flags
                ptl["general_max_12bit_constraint_flag"] = reader.read_bit()
                ptl["general_max_10bit_constraint_flag"] = reader.read_bit()
                ptl["general_max_8bit_constraint_flag"] = reader.read_bit()
                ptl["general_max_422chroma_constraint_flag"] = reader.read_bit()
                ptl["general_max_420chroma_constraint_flag"] = reader.read_bit()
                ptl["general_max_monochrome_constraint_flag"] = reader.read_bit()
                ptl["general_intra_constraint_flag"] = reader.read_bit()
                ptl["general_one_picture_only_constraint_flag"] = reader.read_bit()
                ptl["general_lower_bit_rate_constraint_flag"] = reader.read_bit()
                
                if (profile_idc == 5 or compatibility_flags[5] or
                    profile_idc == 9 or compatibility_flags[9] or
                    profile_idc == 10 or compatibility_flags[10] or
                    profile_idc == 11 or compatibility_flags[11]):
                    ptl["general_max_14bit_constraint_flag"] = reader.read_bit()
                    ptl["general_reserved_zero_33bits"] = reader.read_bits(33)
                else:
                    ptl["general_reserved_zero_34bits"] = reader.read_bits(34)
                    
            elif profile_idc == 2 or compatibility_flags[2]:
                ptl["general_reserved_zero_7bits"] = reader.read_bits(7)
                ptl["general_one_picture_only_constraint_flag"] = reader.read_bit()
                ptl["general_reserved_zero_35bits"] = reader.read_bits(35)
            else:
                ptl["general_reserved_zero_43bits"] = reader.read_bits(43)
            
            # Parse inbld flag conditionally
            if (profile_idc == 1 or compatibility_flags[1] or
                profile_idc == 2 or compatibility_flags[2] or
                profile_idc == 3 or compatibility_flags[3] or
                profile_idc == 4 or compatibility_flags[4] or
                profile_idc == 5 or compatibility_flags[5] or
                profile_idc == 9 or compatibility_flags[9] or
                profile_idc == 11 or compatibility_flags[11]):
                ptl["general_inbld_flag"] = reader.read_bit()
            else:
                ptl["general_reserved_zero_bit"] = reader.read_bit()
        
        # Parse general level IDC
        ptl["general_level_idc"] = reader.read_bits(8)
        
        # Parse sub-layer presence flags
        for i in range(max_num_sub_layers_minus1):
            ptl[f"sub_layer_profile_present_flag[i={i}]"] = reader.read_bit()
            ptl[f"sub_layer_level_present_flag[i={i}]"] = reader.read_bit()
        
        # Skip reserved bits for remaining sub-layers
        if max_num_sub_layers_minus1 > 0:
            for i in range(max_num_sub_layers_minus1, 8):
                ptl[f"reserved_zero_2bits[i={i}]"] = reader.read_bits(2)
        
        # Parse sub-layer profile and level information
        for i in range(max_num_sub_layers_minus1):
            if ptl[f"sub_layer_profile_present_flag[i={i}]"]:
                # Parse sub-layer profile information
                ptl[f"sub_layer_profile_space[i={i}]"] = reader.read_bits(2)
                ptl[f"sub_layer_tier_flag[i={i}]"] = reader.read_bit()
                ptl[f"sub_layer_profile_idc[i={i}]"] = reader.read_bits(5)
                
                # Parse sub-layer profile compatibility flags
                for j in range(32):
                    ptl[f"sub_layer_profile_compatibility_flag[i={i}][j={j}]"] = reader.read_bit()
                
                # Parse sub-layer source and constraint flags
                ptl[f"sub_layer_progressive_source_flag[i={i}]"] = reader.read_bit()
                ptl[f"sub_layer_interlaced_source_flag[i={i}]"] = reader.read_bit()
                ptl[f"sub_layer_non_packed_constraint_flag[i={i}]"] = reader.read_bit()
                ptl[f"sub_layer_frame_only_constraint_flag[i={i}]"] = reader.read_bit()
                
                # Conditional parsing for sub-layer
                sub_profile_idc = ptl[f"sub_layer_profile_idc[i={i}]"]
                sub_compatibility_flags = [ptl[f"sub_layer_profile_compatibility_flag[i={i}][j={j}]"] for j in range(32)]
                
                if (sub_profile_idc == 4 or sub_compatibility_flags[4] or 
                    sub_profile_idc == 5 or sub_compatibility_flags[5] or
                    sub_profile_idc == 6 or sub_compatibility_flags[6] or
                    sub_profile_idc == 7 or sub_compatibility_flags[7] or
                    sub_profile_idc == 8 or sub_compatibility_flags[8] or
                    sub_profile_idc == 9 or sub_compatibility_flags[9] or
                    sub_profile_idc == 10 or sub_compatibility_flags[10] or
                    sub_profile_idc == 11 or sub_compatibility_flags[11]):
                    
                    ptl[f"sub_layer_max_12bit_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_max_10bit_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_max_8bit_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_max_422chroma_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_max_420chroma_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_max_monochrome_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_intra_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_one_picture_only_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_lower_bit_rate_constraint_flag[i={i}]"] = reader.read_bit()
                    
                    if (sub_profile_idc == 5 or sub_compatibility_flags[5] or
                        sub_profile_idc == 9 or sub_compatibility_flags[9] or
                        sub_profile_idc == 10 or sub_compatibility_flags[10] or
                        sub_profile_idc == 11 or sub_compatibility_flags[11]):
                        ptl[f"sub_layer_max_14bit_constraint_flag[i={i}]"] = reader.read_bit()
                        ptl[f"sub_layer_reserved_zero_33bits[i={i}]"] = reader.read_bits(33)
                    else:
                        ptl[f"sub_layer_reserved_zero_34bits[i={i}]"] = reader.read_bits(34)
                        
                elif sub_profile_idc == 2 or sub_compatibility_flags[2]:
                    ptl[f"sub_layer_reserved_zero_7bits[i={i}]"] = reader.read_bits(7)
                    ptl[f"sub_layer_one_picture_only_constraint_flag[i={i}]"] = reader.read_bit()
                    ptl[f"sub_layer_reserved_zero_35bits[i={i}]"] = reader.read_bits(35)
                else:
                    ptl[f"sub_layer_reserved_zero_43bits[i={i}]"] = reader.read_bits(43)
                
                # Parse sub-layer inbld flag conditionally
                if (sub_profile_idc == 1 or sub_compatibility_flags[1] or
                    sub_profile_idc == 2 or sub_compatibility_flags[2] or
                    sub_profile_idc == 3 or sub_compatibility_flags[3] or
                    sub_profile_idc == 4 or sub_compatibility_flags[4] or
                    sub_profile_idc == 5 or sub_compatibility_flags[5] or
                    sub_profile_idc == 9 or sub_compatibility_flags[9] or
                    sub_profile_idc == 11 or sub_compatibility_flags[11]):
                    ptl[f"sub_layer_inbld_flag[i={i}]"] = reader.read_bit()
                else:
                    ptl[f"sub_layer_reserved_zero_bit[i={i}]"] = reader.read_bit()
            
            if ptl[f"sub_layer_level_present_flag[i={i}]"]:
                ptl[f"sub_layer_level_idc[i={i}]"] = reader.read_bits(8)

    except Error as e:
        print(f"PTL parsing error: {str(e)}")
        return {}

    return ptl
