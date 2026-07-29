"""
    Parsing of AVC SPS (Sequence Parameter Set).
"""

from bitstring import Error
from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention
from .vui import parse_vui_parameters


def parse_scaling_list(reader, size_of_scaling_list):
    """Parse scaling list"""
    last_scale = 8
    next_scale = 8
    scaling_list = []
    
    for i in range(size_of_scaling_list):
        if next_scale != 0:
            delta_scale = reader.read_se()
            next_scale = (last_scale + delta_scale + 256) % 256
            scaling_list.append(next_scale)
        else:
            scaling_list.append(last_scale)
        last_scale = scaling_list[-1] if scaling_list else 8
    
    return scaling_list


def parse_sps(data):
    """Parse AVC Sequence Parameter Set"""
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(data)
        if not clean_data:
            return None
        
        reader = BitReader(clean_data)
        sps = {}
        
        # Parse SPS fields
        sps["profile_idc"] = reader.read_bits(8)
        
        # Constraint flags
        sps["constraint_set0_flag"] = reader.read_bit()
        sps["constraint_set1_flag"] = reader.read_bit()
        sps["constraint_set2_flag"] = reader.read_bit()
        sps["constraint_set3_flag"] = reader.read_bit()
        sps["constraint_set4_flag"] = reader.read_bit()
        sps["constraint_set5_flag"] = reader.read_bit()
        
        # Reserved bits
        reserved_zero_2bits = reader.read_bits(2)
        
        sps["level_idc"] = reader.read_bits(8)
        
        sps["seq_parameter_set_id"] = reader.read_ue()
        
        # Chroma format IDC (for High profile and above)
        if sps["profile_idc"] in [100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135]:
            sps["chroma_format_idc"] = reader.read_ue()
            
            if sps["chroma_format_idc"] == 3:
                sps["separate_colour_plane_flag"] = reader.read_bit()
            
            sps["bit_depth_luma_minus8"] = reader.read_ue()
            sps["bit_depth_chroma_minus8"] = reader.read_ue()
            
            sps["qpprime_y_zero_transform_bypass_flag"] = reader.read_bit()
            
            sps["seq_scaling_matrix_present_flag"] = reader.read_bit()
            
            if sps["seq_scaling_matrix_present_flag"]:
                # Parse scaling lists (simplified - just skip)
                for i in range(8 if sps["chroma_format_idc"] != 3 else 12):
                    sps[f"seq_scaling_list_present_flag[i={i}]"] = reader.read_bit()
                    if sps[f"seq_scaling_list_present_flag[i={i}]"]:
                        if i < 6:
                            parse_scaling_list(reader, 16)
                        else:
                            parse_scaling_list(reader, 64)
        else:
            sps["chroma_format_idc"] = 1  # Default for non-High profiles
        
        sps["log2_max_frame_num_minus4"] = reader.read_ue()
        
        sps["pic_order_cnt_type"] = reader.read_ue()
        
        if sps["pic_order_cnt_type"] == 0:
            sps["log2_max_pic_order_cnt_lsb_minus4"] = reader.read_ue()
        elif sps["pic_order_cnt_type"] == 1:
            sps["delta_pic_order_always_zero_flag"] = reader.read_bit()
            sps["offset_for_non_ref_pic"] = reader.read_se()
            sps["offset_for_top_to_bottom_field"] = reader.read_se()
            sps["num_ref_frames_in_pic_order_cnt_cycle"] = reader.read_ue()
            
            for i in range(sps["num_ref_frames_in_pic_order_cnt_cycle"]):
                sps[f"offset_for_ref_frame[i={i}]"] = reader.read_se()
        
        sps["max_num_ref_frames"] = reader.read_ue()
        
        sps["gaps_in_frame_num_value_allowed_flag"] = reader.read_bit()
        
        sps["pic_width_in_mbs_minus1"] = reader.read_ue()
        
        sps["pic_height_in_map_units_minus1"] = reader.read_ue()
        
        sps["frame_mbs_only_flag"] = reader.read_bit()
        
        if not sps["frame_mbs_only_flag"]:
            sps["mb_adaptive_frame_field_flag"] = reader.read_bit()
        
        sps["direct_8x8_inference_flag"] = reader.read_bit()
        
        sps["frame_cropping_flag"] = reader.read_bit()
        
        if sps["frame_cropping_flag"]:
            sps["frame_crop_left_offset"] = reader.read_ue()
            sps["frame_crop_right_offset"] = reader.read_ue()
            sps["frame_crop_top_offset"] = reader.read_ue()
            sps["frame_crop_bottom_offset"] = reader.read_ue()
        
        sps["vui_parameters_present_flag"] = reader.read_bit()
        
        if sps["vui_parameters_present_flag"]:
            vui_info = parse_vui_parameters(reader)
            if vui_info:
                # Nest VUI parameters inside VUIParameters element
                sps["VUIParameters"] = vui_info
        
        return sps
        
    except Error as e:
        print(f"SPS parsing error: {str(e)}")
        return None
