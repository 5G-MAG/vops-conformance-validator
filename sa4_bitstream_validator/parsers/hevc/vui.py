"""
    Parsing of HEVC VUI parameters.
"""

from enum import Enum

from bitstring import Error

class AspectRatioIdc(Enum):
    """Aspect ratio indicator values"""
    UNSPECIFIED     = 0
    SQUARE          = 1
    SAR_12_11       = 2
    SAR_10_11       = 3
    SAR_16_11       = 4
    SAR_40_33       = 5
    SAR_24_11       = 6
    SAR_20_11       = 7
    SAR_32_11       = 8
    SAR_80_33       = 9
    SAR_18_11       = 10
    SAR_15_11       = 11
    SAR_64_33       = 12
    SAR_160_99      = 13
    SAR_4_3_        = 14
    SAR_3_2         = 15
    SAR_2_1         = 16
    EXTENDED_SAR    = 255
    # rest is reserved

def parse_vui_parameters(reader):
    """Parse VUI parameters"""
    vui = {}

    try:

        vui["aspect_ratio_info_present_flag"] = reader.read_bit()
        if vui["aspect_ratio_info_present_flag"]:
            vui["aspect_ratio_idc"] = reader.read_bits(8)
            if vui["aspect_ratio_idc"] == AspectRatioIdc.EXTENDED_SAR:
                vui["sar_width"] = reader.read_bits(16)
                vui["sar_height"] = reader.read_bits(16)

        vui["overscan_info_present_flag"] = reader.read_bit()
        if vui["overscan_info_present_flag"]:
            vui["overscan_appropriate_flag"] = reader.read_bit()

        vui["video_signal_type_present_flag"] = reader.read_bit()
        if vui["video_signal_type_present_flag"]:
            vui["video_format"] = reader.read_bits(3)
            vui["video_full_range_flag"] = reader.read_bit()
            vui["colour_description_present_flag"] = reader.read_bit()
            if vui["colour_description_present_flag"]:
                vui["colour_primaries"] = reader.read_bits(8)
                vui["transfer_characteristics"] = reader.read_bits(8)
                vui["matrix_coeffs"] = reader.read_bits(8)

        vui["chroma_loc_info_present_flag"] = reader.read_bit()
        if vui["chroma_loc_info_present_flag"]:
            vui["chroma_sample_loc_type_top_field"] = reader.read_ue()
            vui["chroma_sample_loc_type_bottom_field"] = reader.read_ue()

        vui["neutral_chroma_indication_flag"] = reader.read_bit()
        vui["field_seq_flag"] = reader.read_bit()
        vui["frame_field_info_present_flag"] = reader.read_bit()
        vui["default_display_window_flag"] = reader.read_bit()
        if vui["default_display_window_flag"]:
            vui["def_disp_win_left_offset"] = reader.read_ue()
            vui["def_disp_win_right_offset"] = reader.read_ue()
            vui["def_disp_win_top_offset"] = reader.read_ue()
            vui["chroma_sample_loc_type_bottom_field"] = reader.read_ue()

        vui["vui_timing_info_present_flag"] = reader.read_bit()
        if vui["vui_timing_info_present_flag"]:
            vui["vui_num_units_in_tick"] = reader.read_bits(32)
            vui["vui_time_scale"] = reader.read_bits(32)
            vui["vui_poc_proportional_to_timing_flag"] = reader.read_bit()
            if vui["vui_poc_proportional_to_timing_flag"]:
                vui["vui_num_ticks_poc_diff_one_minus1"] = reader.read_ue()

            vui["vui_hrd_parameters_present_flag"] = reader.read_bit()
            if vui["vui_hrd_parameters_present_flag"]:
                assert False
                #TODO: hrd_paremeters()

            vui["bitstream_restriction_flag"] = reader.read_bit()
            if vui["bitstream_restriction_flag"]:
                vui["tiles_fixed_structure_flag"] = reader.read_bit()
                vui["motion_vectors_over_pic_boundaries_flag"] = reader.read_bit()
                vui["restricted_ref_pic_lists_flag"] = reader.read_bit()
                vui["min_spatial_segmentation_idc"] = reader.read_ue()
                vui["max_bytes_per_pic_denom"] = reader.read_ue()
                vui["max_bits_per_min_cu_denom"] = reader.read_ue()
                vui["log2_max_mv_length_horizontal"] = reader.read_ue()
                vui["log2_max_mv_length_vertical"] = reader.read_ue()

    except Error as e:
        print(f"Short-term reference picture set parsing error: {e}")
        return None

    return vui
