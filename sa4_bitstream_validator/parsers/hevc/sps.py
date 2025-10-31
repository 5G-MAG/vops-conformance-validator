"""
    Parsing of HEVC SPS.
"""

from bitstring import Error

from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention
from .ptl import parse_profile_tier_level
from .st_ref_pic_set import parse_st_ref_pic_sets
from .vui import parse_vui_parameters

def parse_scaling_list_data(reader):
    """Parse scaling list data"""
    scaling_list = {}
    
    for size_id in range(4):
        for matrix_id in range(6 if size_id == 3 else (3 if size_id < 2 else 2)):
            scaling_list_pred_mode_flag = reader.read_bit()
            scaling_list[f"scaling_list_pred_mode_flag[{size_id}][{matrix_id}]"] = scaling_list_pred_mode_flag
            
            if not scaling_list_pred_mode_flag:
                scaling_list[f"scaling_list_pred_matrix_id_delta[{size_id}][{matrix_id}]"] = reader.read_ue()
            else:
                next_coef = 8
                coef_num = min(64, (1 << (4 + (size_id << 1))))
                
                if size_id > 1:
                    scaling_list[f"scaling_list_dc_coef_minus8[{size_id - 2}][{matrix_id}]"] = reader.read_se()
                    next_coef = scaling_list[f"scaling_list_dc_coef_minus8[{size_id - 2}][{matrix_id}]"] + 8
                
                for i in range(coef_num):
                    scaling_list[f"scaling_list_delta_coef[{size_id}][{matrix_id}][{i}]"] = reader.read_se()
    
    return scaling_list

def parse_sps(payload_data, nuh_layer_id):
    """Parse Sequence Parameter Set from payload bytes"""
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(payload_data)
        if not clean_data:
            return None

        reader = BitReader(clean_data)
        sps = {}
        sps["sps_video_parameter_set_id"] = reader.read_bits(4)
        if nuh_layer_id == 0:
            sps["sps_max_sub_layers_minus1"] = reader.read_bits(3)
        else:
            sps["sps_ext_or_max_sub_layers_minus1"] = reader.read_bits(3)

        multi_layer_ext_sps_flag = (nuh_layer_id != 0
                                    and sps["sps_ext_or_max_sub_layers_minus1"] == 7)
        if not multi_layer_ext_sps_flag:
            sps["sps_temporal_id_nesting_flag"] = reader.read_bit()

            sps = {
                    **sps,
                    **parse_profile_tier_level(True, sps["sps_max_sub_layers_minus1"], reader)
            }

        sps["sps_seq_parameter_set_id"] = reader.read_ue()
        
        if multi_layer_ext_sps_flag:
            # Multi-layer SPS parsing path
            sps["update_rep_format_flag"] = reader.read_bit()
            if sps["update_rep_format_flag"]:
                sps["sps_rep_format_idx"] = reader.read_bits(8)
            
            # Multi-layer specific fields
            sps["log2_max_pic_order_cnt_lsb_minus4"] = reader.read_ue()
            sps["log2_min_luma_coding_block_size_minus3"] = reader.read_ue()
            sps["log2_diff_max_min_luma_coding_block_size"] = reader.read_ue()
            sps["log2_min_luma_transform_block_size_minus2"] = reader.read_ue()
            sps["log2_diff_max_min_luma_transform_block_size"] = reader.read_ue()
            sps["max_transform_hierarchy_depth_inter"] = reader.read_ue()
            sps["max_transform_hierarchy_depth_intra"] = reader.read_ue()
            sps["scaling_list_enabled_flag"] = reader.read_bit()
            
            if sps["scaling_list_enabled_flag"]:
                sps["sps_infer_scaling_list_flag"] = reader.read_bit()
                if not sps["sps_infer_scaling_list_flag"]:
                    sps["sps_scaling_list_data_present_flag"] = reader.read_bit()
                    if sps["sps_scaling_list_data_present_flag"]:
                        scaling_list_data = parse_scaling_list_data(reader)
                        sps.update(scaling_list_data)
            
            sps["amp_enabled_flag"] = reader.read_bit()
            sps["sample_adaptive_offset_enabled_flag"] = reader.read_bit()
            sps["pcm_enabled_flag"] = reader.read_bit()
            
            sps["num_short_term_ref_pic_sets"] = reader.read_ue()
            sps = {
                    **sps,
                    **parse_st_ref_pic_sets(sps["num_short_term_ref_pic_sets"], False, reader)
            }

            sps["long_term_ref_pics_present_flag"] = reader.read_bit()
            if sps["long_term_ref_pics_present_flag"]:
                sps["num_long_term_ref_pics_sps"] = reader.read_ue()
                lt_ref_pic_length = sps["log2_max_pic_order_cnt_lsb_minus4"] + 4
                for i in range(0, sps["num_long_term_ref_pics_sps"]):
                    sps[f"lt_ref_pic_poc_lsb_sps[{i}]"] = reader.read_bits(lt_ref_pic_length)
                    sps[f"used_by_curr_pic_lt_sps_flag[{i}]"] = reader.read_bit()

            sps["sps_temporal_mvp_enabled_flag"] = reader.read_bit()
            sps["strong_intra_smoothing_enabled_flag"] = reader.read_bit()
            sps["vui_parameters_present_flag"] = reader.read_bit()
            
            # SPS extension flags for multi-layer SPS
            sps["sps_extension_present_flag"] = reader.read_bit()
            if sps["sps_extension_present_flag"]:
                sps["sps_range_extension_flag"] = reader.read_bit()
                sps["sps_multilayer_extension_flag"] = reader.read_bit()
                sps["sps_extension_1bit"] = reader.read_bit()
                sps["sps_scc_extension_flag"] = reader.read_bit()
                
                # Skip the remaining extension bits (reserved for future use)
                for _ in range(3):
                    reader.read_bit()
                
                # Parse multilayer extension if present
                if sps["sps_multilayer_extension_flag"]:
                    sps["inter_view_mv_vert_constraint_flag"] = reader.read_bit()
        else:
            # Non-multi-layer SPS parsing path
            sps["chroma_format_idc"] = reader.read_ue()

            if sps["chroma_format_idc"] == 2:
                sps["separate_colour_plane_flag"] = reader.read_bit()

            sps["pic_width_in_luma_samples"] = reader.read_ue()
            sps["pic_height_in_luma_samples"] = reader.read_ue()
            sps["conformance_window_flag"] = reader.read_bit()

            if sps["conformance_window_flag"]:
                sps["conf_win_left_offset"] = reader.read_ue()
                sps["conf_win_right_offset"] = reader.read_ue()
                sps["conf_win_top_offset"] = reader.read_ue()
                sps["conf_win_bottom_offset"] = reader.read_ue()

            sps["bit_depth_luma_minus8"] = reader.read_ue()
            sps["bit_depth_chroma_minus8"] = reader.read_ue()

            sps["log2_max_pic_order_cnt_lsb_minus4"] = reader.read_ue()
            sps["sps_sub_layer_ordering_info_present_flag"] = reader.read_bit()
            init_value = (0 if sps["sps_sub_layer_ordering_info_present_flag"]
                          else sps["sps_max_sub_layers_minus1"])
            for i in range(init_value, sps["sps_max_sub_layers_minus1"]+1):
                sps[f"sps_max_dec_pic_buffering_minus1[{i}]"] = reader.read_ue()
                sps[f"sps_max_num_reorder_pics[{i}]"] = reader.read_ue()
                sps[f"sps_max_latency_increase_plus1[{i}]"] = reader.read_ue()

            sps["log2_min_luma_coding_block_size_minus3"] = reader.read_ue()
            sps["log2_diff_max_min_luma_coding_block_size"] = reader.read_ue()
            sps["log2_min_luma_transform_block_size_minus2"] = reader.read_ue()
            sps["log2_diff_max_min_luma_transform_block_size"] = reader.read_ue()
            sps["max_transform_hierarchy_depth_inter"] = reader.read_ue()
            sps["max_transform_hierarchy_depth_intra"] = reader.read_ue()
            sps["scaling_list_enabled_flag"] = reader.read_bit()
            if sps["scaling_list_enabled_flag"]:
                sps["sps_scaling_list_data_present_flag"] = reader.read_bit()
                if sps["sps_scaling_list_data_present_flag"]:
                    scaling_list_data = parse_scaling_list_data(reader)
                    sps.update(scaling_list_data)

            sps["amp_enabled_flag"] = reader.read_bit()
            sps["sample_adaptive_offset_enabled_flag"] = reader.read_bit()
            sps["pcm_enabled_flag"] = reader.read_bit()
            if sps["pcm_enabled_flag"]:
                sps["pcm_sample_bit_depth_luma_minus1"] = reader.read_bits(4)
                sps["pcm_sample_bit_depth_chroma_minus1"] = reader.read_bits(4)
                sps["log2_min_pcm_luma_coding_block_size_minus3"] = reader.read_ue()
                sps["log2_diff_max_min_pcm_luma_coding_block_size"] = reader.read_ue()
                sps["pcm_loop_filter_disabled_flag"] = reader.read_bit()

            sps["num_short_term_ref_pic_sets"] = reader.read_ue()
            sps = {
                    **sps,
                    **parse_st_ref_pic_sets(sps["num_short_term_ref_pic_sets"], False, reader)
            }

            sps["long_term_ref_pics_present_flag"] = reader.read_bit()
            if sps["long_term_ref_pics_present_flag"]:
                sps["num_long_term_ref_pics_sps"] = reader.read_ue()
                lt_ref_pic_length = sps["log2_max_pic_order_cnt_lsb_minus4"] + 4
                for i in range(0, sps["num_long_term_ref_pics_sps"]):
                    sps[f"lt_ref_pic_poc_lsb_sps[{i}]"] = reader.read_bits(lt_ref_pic_length)
                    sps[f"used_by_curr_pic_lt_sps_flag[{i}]"] = reader.read_bit()

            sps["sps_temporal_mvp_enabled_flag"] = reader.read_bit()
            sps["strong_intra_smoothing_enabled_flag"] = reader.read_bit()
            sps["vui_parameters_present_flag"] = reader.read_bit()
            if sps["vui_parameters_present_flag"]:
                sps = {
                        **sps,
                        **parse_vui_parameters(reader)
                }

            # SPS extension flags for non-multi-layer SPS
            sps["sps_extension_present_flag"] = reader.read_bit()
            if sps["sps_extension_present_flag"]:
                sps["sps_range_extension_flag"] = reader.read_bit()
                sps["sps_multilayer_extension_flag"] = reader.read_bit()
                sps["sps_extension_1bit"] = reader.read_bit()
                sps["sps_scc_extension_flag"] = reader.read_bit()
                
                # Skip the remaining extension bits (reserved for future use)
                for _ in range(3):
                    reader.read_bit()

        return {k: v for k, v in sps.items() if v is not None}

    except Error as e:
        print(f"SPS parsing error: {str(e)}")
        return None
