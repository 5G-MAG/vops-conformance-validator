"""
    Parsing of AVC VUI parameters and HRD parameters.
"""

from bitstring import Error


def parse_hrd_parameters(reader):
    """Parse HRD parameters"""
    hrd = {}
    
    hrd["cpb_cnt_minus1"] = reader.read_ue()
    hrd["bit_rate_scale"] = reader.read_bits(4)
    hrd["cpb_size_scale"] = reader.read_bits(4)
    
    # Parse bit_rate_value_minus1 and cpb_size_value_minus1 for each SchedSelIdx
    for i in range(hrd["cpb_cnt_minus1"] + 1):
        hrd[f"bit_rate_value_minus1[{i}]"] = reader.read_ue()
        hrd[f"cpb_size_value_minus1[{i}]"] = reader.read_ue()
        hrd[f"cbr_flag[{i}]"] = reader.read_bit()
    
    hrd["initial_cpb_removal_delay_length_minus1"] = reader.read_bits(5)
    hrd["cpb_removal_delay_length_minus1"] = reader.read_bits(5)
    hrd["dpb_output_delay_length_minus1"] = reader.read_bits(5)
    hrd["time_offset_length"] = reader.read_bits(5)
    
    return hrd


def calculate_bit_rate(bit_rate_value_minus1, bit_rate_scale):
    """Calculate bit rate using AVC spec formula E-81
    
    BitRate = (bit_rate_value_minus1 + 1) * 2^(6 + bit_rate_scale)
    """
    return (bit_rate_value_minus1 + 1) * (1 << (6 + bit_rate_scale))


def parse_vui_parameters(reader):
    """Parse AVC VUI parameters"""
    try:
        vui = {}
        
        vui["aspect_ratio_info_present_flag"] = reader.read_bit()
        
        if vui["aspect_ratio_info_present_flag"]:
            vui["aspect_ratio_idc"] = reader.read_bits(8)
            
            # Extended_SAR
            if vui["aspect_ratio_idc"] == 255:
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
                vui["matrix_coefficients"] = reader.read_bits(8)
        
        vui["chroma_loc_info_present_flag"] = reader.read_bit()
        
        if vui["chroma_loc_info_present_flag"]:
            vui["chroma_sample_loc_type_top_field"] = reader.read_ue()
            vui["chroma_sample_loc_type_bottom_field"] = reader.read_ue()
        
        vui["timing_info_present_flag"] = reader.read_bit()
        
        if vui["timing_info_present_flag"]:
            vui["num_units_in_tick"] = reader.read_bits(32)
            vui["time_scale"] = reader.read_bits(32)
            vui["fixed_frame_rate_flag"] = reader.read_bit()
        
        vui["nal_hrd_parameters_present_flag"] = reader.read_bit()
        
        if vui["nal_hrd_parameters_present_flag"]:
            nal_hrd = parse_hrd_parameters(reader)
            # Store with prefix for NAL HRD
            for key, value in nal_hrd.items():
                vui[f"nal_hrd_{key}"] = value
        
        vui["vcl_hrd_parameters_present_flag"] = reader.read_bit()
        
        if vui["vcl_hrd_parameters_present_flag"]:
            vcl_hrd = parse_hrd_parameters(reader)
            # Store with prefix for VCL HRD
            for key, value in vcl_hrd.items():
                vui[f"vcl_hrd_{key}"] = value
            
            # Calculate VCL bit rate for each SchedSelIdx
            cpb_cnt = vcl_hrd["cpb_cnt_minus1"]
            bit_rate_scale = vcl_hrd["bit_rate_scale"]
            
            for i in range(cpb_cnt + 1):
                bit_rate_value_minus1 = vcl_hrd[f"bit_rate_value_minus1[{i}]"]
                vcl_bit_rate = calculate_bit_rate(bit_rate_value_minus1, bit_rate_scale)
                vui[f"_vcl_bit_rate[{i}]"] = vcl_bit_rate
        
        if vui["nal_hrd_parameters_present_flag"] or vui["vcl_hrd_parameters_present_flag"]:
            vui["low_delay_hrd_flag"] = reader.read_bit()
        
        vui["pic_struct_present_flag"] = reader.read_bit()
        
        vui["bitstream_restriction_flag"] = reader.read_bit()
        
        if vui["bitstream_restriction_flag"]:
            vui["motion_vectors_over_pic_boundaries_flag"] = reader.read_bit()
            vui["max_bytes_per_pic_denom"] = reader.read_ue()
            vui["max_bits_per_mb_denom"] = reader.read_ue()
            vui["log2_max_mv_length_horizontal"] = reader.read_ue()
            vui["log2_max_mv_length_vertical"] = reader.read_ue()
            vui["max_num_reorder_frames"] = reader.read_ue()
            vui["max_dec_frame_buffering"] = reader.read_ue()
        
        return vui
        
    except Error as e:
        print(f"VUI parsing error: {str(e)}")
        return None
