"""
    Parsing of AVC PPS (Picture Parameter Set).
"""

from bitstring import Error
from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention


def parse_pps(data):
    """Parse AVC Picture Parameter Set"""
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(data)
        if not clean_data:
            return None
        
        reader = BitReader(clean_data)
        pps = {}
        
        pps["pic_parameter_set_id"] = reader.read_ue()
        pps["seq_parameter_set_id"] = reader.read_ue()
        
        pps["entropy_coding_mode_flag"] = reader.read_bit()
        
        pps["bottom_field_pic_order_in_frame_present_flag"] = reader.read_bit()
        
        pps["num_slice_groups_minus1"] = reader.read_ue()
        
        if pps["num_slice_groups_minus1"] > 0:
            pps["slice_group_map_type"] = reader.read_ue()
            
            if pps["slice_group_map_type"] == 0:
                for i in range(pps["num_slice_groups_minus1"] + 1):
                    pps[f"run_length_minus1[i={i}]"] = reader.read_ue()
            elif pps["slice_group_map_type"] == 2:
                for i in range(pps["num_slice_groups_minus1"]):
                    pps[f"top_left[i={i}]"] = reader.read_ue()
                    pps[f"bottom_right[i={i}]"] = reader.read_ue()
            elif pps["slice_group_map_type"] in [3, 4, 5]:
                pps["slice_group_change_direction_flag"] = reader.read_bit()
                pps["slice_group_change_rate_minus1"] = reader.read_ue()
            elif pps["slice_group_map_type"] == 6:
                pps["pic_size_in_map_units_minus1"] = reader.read_ue()
                bits_needed = max(1, (pps["num_slice_groups_minus1"] + 1).bit_length())
                for i in range(pps["pic_size_in_map_units_minus1"] + 1):
                    pps[f"slice_group_id[i={i}]"] = reader.read_bits(bits_needed)
        
        pps["num_ref_idx_l0_active_minus1"] = reader.read_ue()
        pps["num_ref_idx_l1_active_minus1"] = reader.read_ue()
        
        pps["weighted_pred_flag"] = reader.read_bit()
        pps["weighted_bipred_idc"] = reader.read_bits(2)
        
        pps["pic_init_qp_minus26"] = reader.read_se()
        pps["pic_init_qs_minus26"] = reader.read_se()
        
        pps["chroma_qp_index_offset"] = reader.read_se()
        
        pps["deblocking_filter_control_present_flag"] = reader.read_bit()
        pps["constrained_intra_pred_flag"] = reader.read_bit()
        pps["redundant_pic_cnt_present_flag"] = reader.read_bit()
        
        # Check if we have more bits to read
        # The transform_8x8_mode_flag and related fields are only present in High profile
        # and when there are more RBSP data
        if reader.remaining_bits() > 0:
            try:
                pps["transform_8x8_mode_flag"] = reader.read_bit()
                
                pps["pic_scaling_matrix_present_flag"] = reader.read_bit()
                
                if pps["pic_scaling_matrix_present_flag"]:
                    # Parse scaling lists for PPS
                    # The number of scaling lists depends on chroma_format_idc
                    # For simplicity, we'll parse 8 scaling lists (6 for luma + 2 for chroma)
                    # In a full implementation, we would look up chroma_format_idc from SPS
                    for i in range(8):
                        pps[f"pic_scaling_list_present_flag[i={i}]"] = reader.read_bit()
                        if pps[f"pic_scaling_list_present_flag[i={i}]"]:
                            # Parse scaling list (simplified - just skip)
                            if i < 6:
                                # Luma scaling list (4x4)
                                size_of_scaling_list = 16
                            else:
                                # Chroma scaling list (4x4)
                                size_of_scaling_list = 16
                            
                            last_scale = 8
                            next_scale = 8
                            for j in range(size_of_scaling_list):
                                if next_scale != 0:
                                    delta_scale = reader.read_se()
                                    next_scale = (last_scale + delta_scale + 256) % 256
                                last_scale = next_scale
                
                pps["second_chroma_qp_index_offset"] = reader.read_se()
            except:
                # If parsing fails, these fields are not present
                pass
        
        return pps
        
    except Error as e:
        print(f"PPS parsing error: {str(e)}")
        return None
