"""
    Parsing of HEVC SPS.
"""

from bitstring import Error

from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention
from .ptl import parse_profile_tier_level
from .st_ref_pic_set import parse_st_ref_pic_sets

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
            sps["update_rep_format_flag"] = reader.read_bit()
            if sps["update_rep_format_flag"]:
                sps["sps_rep_format_idx"] = reader.read_bits(8)
        else:
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
        if not multi_layer_ext_sps_flag:
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

        assert not sps["scaling_list_enabled_flag"]
        #NOTE: Scaling list enabled flag true, not implemented

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

        return {k: v for k, v in sps.items() if v is not None}

    except Error as e:
        print(f"SPS parsing error: {str(e)}")
        return None
