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
            scaling_list[f"scaling_list_pred_mode_flag[size_id={size_id}][matrix_id={matrix_id}]"] = scaling_list_pred_mode_flag
            
            if not scaling_list_pred_mode_flag:
                scaling_list[f"scaling_list_pred_matrix_id_delta[size_id={size_id}][matrix_id={matrix_id}]"] = reader.read_ue()
            else:
                next_coef = 8
                coef_num = min(64, (1 << (4 + (size_id << 1))))
                
                if size_id > 1:
                    scaling_list[f"scaling_list_dc_coef_minus8[size_id={size_id - 2}][matrix_id={matrix_id}]"] = reader.read_se()
                    next_coef = scaling_list[f"scaling_list_dc_coef_minus8[size_id={size_id - 2}][matrix_id={matrix_id}]"] + 8
                
                for i in range(coef_num):
                    scaling_list[f"scaling_list_delta_coef[size_id={size_id}][matrix_id={matrix_id}][i={i}]"] = reader.read_se()
    
    return scaling_list

def parse_sps_range_extension(reader):
    """Parse SPS range extension data"""
    sps_range = {}
    sps_range["transform_skip_rotation_enabled_flag"] = reader.read_bit()
    sps_range["transform_skip_context_enabled_flag"] = reader.read_bit()
    sps_range["implicit_rdpcm_enabled_flag"] = reader.read_bit()
    sps_range["explicit_rdpcm_enabled_flag"] = reader.read_bit()
    sps_range["extended_precision_processing_flag"] = reader.read_bit()
    sps_range["intra_smoothing_disabled_flag"] = reader.read_bit()
    sps_range["high_precision_offsets_enabled_flag"] = reader.read_bit()
    sps_range["persistent_rice_adaptation_enabled_flag"] = reader.read_bit()
    sps_range["cabac_bypass_alignment_enabled_flag"] = reader.read_bit()
    return sps_range

def parse_sps_multilayer_extension(reader):
    """Parse SPS multilayer extension data"""
    sps_multilayer = {}
    sps_multilayer["inter_view_mv_vert_constraint_flag"] = reader.read_bit()
    return sps_multilayer

def parse_sps_3d_extension(reader):
    """Parse SPS 3D extension data (Annex I)"""
    sps_3d = {}
    sps_3d["iv_di_mc_enabled_flag"] = reader.read_bit()
    sps_3d["iv_mv_scal_enabled_flag"] = reader.read_bit()
    
    if sps_3d["iv_di_mc_enabled_flag"] or sps_3d["iv_mv_scal_enabled_flag"]:
        sps_3d["log2_ivmc_sub_pb_size_minus3"] = reader.read_ue()
        sps_3d["iv_res_pred_enabled_flag"] = reader.read_bit()
        sps_3d["depth_ref_enabled_flag"] = reader.read_bit()
        sps_3d["vsp_mc_enabled_flag"] = reader.read_bit()
        sps_3d["dbbp_enabled_flag"] = reader.read_bit()
        
        if sps_3d["vsp_mc_enabled_flag"]:
            sps_3d["tex_mc_enabled_flag"] = reader.read_bit()
            
            if sps_3d["tex_mc_enabled_flag"]:
                sps_3d["log2_texmc_sub_pb_size_minus3"] = reader.read_ue()
                
        sps_3d["intra_contour_enabled_flag"] = reader.read_bit()
        sps_3d["intra_dc_only_wedge_enabled_flag"] = reader.read_bit()
        sps_3d["cqt_cu_part_pred_enabled_flag"] = reader.read_bit()
        sps_3d["inter_dc_only_enabled_flag"] = reader.read_bit()
        sps_3d["skip_intra_enabled_flag"] = reader.read_bit()
    
    return sps_3d

def parse_sps_scc_extension(reader):
    """Parse SPS screen content coding extension data"""
    sps_scc = {}
    sps_scc["sps_curr_pic_ref_enabled_flag"] = reader.read_bit()
    sps_scc["palette_mode_enabled_flag"] = reader.read_bit()
    
    if sps_scc["palette_mode_enabled_flag"]:
        sps_scc["palette_max_size"] = reader.read_ue()
        sps_scc["palette_predictor_initializer_present_flag"] = reader.read_bit()
        
        if sps_scc["palette_predictor_initializer_present_flag"]:
            sps_scc["palette_predictor_initializers_num_minus1"] = reader.read_ue()
            
    sps_scc["motion_vector_resolution_control_idc"] = reader.read_bits(2)
    sps_scc["intra_boundary_filtering_disabled_flag"] = reader.read_bit()
    return sps_scc

def parse_common_sps_fields(reader, sps, multi_layer=False):
    """Parse common SPS fields that exist in both multi-layer and non-multi-layer SPS"""
    
    # Common core fields
    sps["log2_min_luma_coding_block_size_minus3"] = reader.read_ue()
    sps["log2_diff_max_min_luma_coding_block_size"] = reader.read_ue()
    sps["log2_min_luma_transform_block_size_minus2"] = reader.read_ue()
    sps["log2_diff_max_min_luma_transform_block_size"] = reader.read_ue()
    sps["max_transform_hierarchy_depth_inter"] = reader.read_ue()
    sps["max_transform_hierarchy_depth_intra"] = reader.read_ue()
    sps["scaling_list_enabled_flag"] = reader.read_bit()
    
    # Scaling list handling with multi-layer variations
    if sps["scaling_list_enabled_flag"]:
        if multi_layer:
            sps["sps_infer_scaling_list_flag"] = reader.read_bit()
            if sps["sps_infer_scaling_list_flag"]:
                sps["sps_scaling_list_ref_layer_id"] = reader.read_bits(6)
            else:
                sps["sps_scaling_list_data_present_flag"] = reader.read_bit()
                if sps["sps_scaling_list_data_present_flag"]:
                    scaling_list_data = parse_scaling_list_data(reader)
                    sps.update(scaling_list_data)
        else:
            sps["sps_scaling_list_data_present_flag"] = reader.read_bit()
            if sps["sps_scaling_list_data_present_flag"]:
                scaling_list_data = parse_scaling_list_data(reader)
                sps.update(scaling_list_data)
    
    # Common flags
    sps["amp_enabled_flag"] = reader.read_bit()
    sps["sample_adaptive_offset_enabled_flag"] = reader.read_bit()
    sps["pcm_enabled_flag"] = reader.read_bit()
    
    # PCM handling with multi-layer variations
    if sps["pcm_enabled_flag"]:
        try:
            sps["pcm_sample_bit_depth_luma_minus1"] = reader.read_bits(4)
            sps["pcm_sample_bit_depth_chroma_minus1"] = reader.read_bits(4)
            sps["log2_min_pcm_luma_coding_block_size_minus3"] = reader.read_ue()
            sps["log2_diff_max_min_pcm_luma_coding_block_size"] = reader.read_ue()
            sps["pcm_loop_filter_disabled_flag"] = reader.read_bit()
        except Exception:
            # If we can't read PCM fields, set PCM flag to false and continue
            sps["pcm_enabled_flag"] = 0
            # Remove any partially set PCM fields
            for field in ["pcm_sample_bit_depth_luma_minus1", "pcm_sample_bit_depth_chroma_minus1", 
                          "log2_min_pcm_luma_coding_block_size_minus3", "log2_diff_max_min_pcm_luma_coding_block_size",
                          "pcm_loop_filter_disabled_flag"]:
                sps.pop(field, None)
    
    # Short-term reference picture sets
    try:
        sps["num_short_term_ref_pic_sets"] = reader.read_ue()
        sps.update(parse_st_ref_pic_sets(sps["num_short_term_ref_pic_sets"], False, reader))
    except Exception:
        # If we can't read short-term reference picture sets, set to 0 and continue
        sps["num_short_term_ref_pic_sets"] = 0
        sps.update(parse_st_ref_pic_sets(0, False, reader))
    
    # Long-term reference pictures
    sps["long_term_ref_pics_present_flag"] = reader.read_bit()
    if sps["long_term_ref_pics_present_flag"]:
        sps["num_long_term_ref_pics_sps"] = reader.read_ue()
        lt_ref_pic_length = sps["log2_max_pic_order_cnt_lsb_minus4"] + 4
        for i in range(sps["num_long_term_ref_pics_sps"]):
            sps[f"lt_ref_pic_poc_lsb_sps[i={i}]"] = reader.read_bits(lt_ref_pic_length)
            sps[f"used_by_curr_pic_lt_sps_flag[i={i}]"] = reader.read_bit()
    
    # Common flags
    sps["sps_temporal_mvp_enabled_flag"] = reader.read_bit()
    sps["strong_intra_smoothing_enabled_flag"] = reader.read_bit()
    
    return sps

def parse_sps_extensions(reader, sps):
    """Parse SPS extension data based on extension flags"""
    sps["sps_extension_present_flag"] = reader.read_bit()
    if sps["sps_extension_present_flag"]:
        sps["sps_range_extension_flag"] = reader.read_bit()
        sps["sps_multilayer_extension_flag"] = reader.read_bit()
        sps["sps_extension_1bit"] = reader.read_bit()
        sps["sps_scc_extension_flag"] = reader.read_bit()
        
        # Parse the extension data based on flags
        if sps["sps_range_extension_flag"]:
            sps_range = parse_sps_range_extension(reader)
            sps.update(sps_range)
        
        if sps["sps_multilayer_extension_flag"]:
            sps_multilayer = parse_sps_multilayer_extension(reader)
            sps.update(sps_multilayer)
        
        if sps["sps_extension_1bit"]:  # This is the 3D extension flag
            sps_3d = parse_sps_3d_extension(reader)
            sps.update(sps_3d)
        
        if sps["sps_scc_extension_flag"]:
            sps_scc = parse_sps_scc_extension(reader)
            sps.update(sps_scc)
        
        # Skip the remaining extension bits (reserved for future use)
        for _ in range(3):
            reader.read_bit()
    
    return sps

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
            # Multi-layer SPS parsing path - unique fields
            sps["update_rep_format_flag"] = reader.read_bit()
            if sps["update_rep_format_flag"]:
                sps["sps_rep_format_idx"] = reader.read_bits(8)
            
            # Multi-layer specific fields before common parsing
            sps["log2_max_pic_order_cnt_lsb_minus4"] = reader.read_ue()
                
        else:
            # Non-multi-layer SPS parsing path - unique fields
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

        # Sub-layer ordering info (unique to non-multi-layer)
        sps["log2_max_pic_order_cnt_lsb_minus4"] = reader.read_ue()
        if not multi_layer_ext_sps_flag:
            sps["sps_sub_layer_ordering_info_present_flag"] = reader.read_bit()
            init_value = (0 if sps["sps_sub_layer_ordering_info_present_flag"]
                            else sps["sps_max_sub_layers_minus1"])
            for i in range(init_value, sps["sps_max_sub_layers_minus1"]+1):
                sps[f"sps_max_dec_pic_buffering_minus1[i={i}]"] = reader.read_ue()
                sps[f"sps_max_num_reorder_pics[i={i}]"] = reader.read_ue()
                sps[f"sps_max_latency_increase_plus1[i={i}]"] = reader.read_ue()

        # Parse common fields with multi_layer=False
        sps = parse_common_sps_fields(reader, sps, multi_layer=False)
        
        # Non-multi-layer specific VUI handling
        sps["vui_parameters_present_flag"] = reader.read_bit()
        if sps["vui_parameters_present_flag"]:
            sps.update(parse_vui_parameters(sps["sps_max_sub_layers_minus1"], reader))

        # Parse extensions for non-multi-layer SPS
        sps = parse_sps_extensions(reader, sps)

        return {k: v for k, v in sps.items() if v is not None}

    except Error as e:
        print(f"SPS parsing error: {str(e)}")
        return None
