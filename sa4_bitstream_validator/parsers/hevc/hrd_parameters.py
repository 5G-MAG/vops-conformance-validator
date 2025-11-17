"""
    Parsing of HEVC HRD (Hypothetical Reference Decoder) parameters.
    This module implements the complete HRD parameter parsing according to HEVC specification.
"""

from bitstring import Error
from sa4_bitstream_validator.bit_reader import BitReader

def parse_hrd_parameters(common_hrd_params_present_flag, max_sub_layers_minus1, reader):
    """
    Parse HRD parameters according to HEVC specification.
    
    Args:
        common_hrd_params_present_flag (bool): Flag indicating if common HRD parameters are present
        max_sub_layers_minus1 (int): Maximum number of temporal sub-layers minus 1
        reader (BitReader): Bit reader instance
    
    Returns:
        dict: Parsed HRD parameters
    """
    try:
        hrd = {}
        
        # Common HRD parameters
        if common_hrd_params_present_flag:
            hrd["nal_hrd_parameters_present_flag"] = reader.read_bit()
            hrd["vcl_hrd_parameters_present_flag"] = reader.read_bit()
            
            if hrd["nal_hrd_parameters_present_flag"] or hrd["vcl_hrd_parameters_present_flag"]:
                hrd["sub_pic_hrd_params_present_flag"] = reader.read_bit()
                
                if hrd["sub_pic_hrd_params_present_flag"]:
                    hrd["tick_divisor_minus2"] = reader.read_bits(8)
                    hrd["du_cpb_removal_delay_increment_length_minus1"] = reader.read_bits(5)
                    hrd["sub_pic_cpb_params_in_pic_timing_sei_flag"] = reader.read_bit()
                    hrd["dpb_output_delay_du_length_minus1"] = reader.read_bits(5)
                
                hrd["bit_rate_scale"] = reader.read_bits(4)
                hrd["cpb_size_scale"] = reader.read_bits(4)
                
                if hrd["sub_pic_hrd_params_present_flag"]:
                    hrd["cpb_size_du_scale"] = reader.read_bits(4)
                
                hrd["initial_cpb_removal_delay_length_minus1"] = reader.read_bits(5)
                hrd["au_cpb_removal_delay_length_minus1"] = reader.read_bits(5)
                hrd["dpb_output_delay_length_minus1"] = reader.read_bits(5)
        
        # Sub-layer HRD parameters
        max_sub_layers = max_sub_layers_minus1 + 1
        
        for i in range(max_sub_layers):
            hrd[f"fixed_pic_rate_general_flag[i={i}]"] = reader.read_bit()
            
            if not hrd[f"fixed_pic_rate_general_flag[i={i}]"]:
                hrd[f"fixed_pic_rate_within_cvs_flag[i={i}]"] = reader.read_bit()
            
            if hrd[f"fixed_pic_rate_within_cvs_flag[i={i}]"]:
                hrd[f"elemental_duration_in_tc_minus1[i={i}]"] = reader.read_ue()
            else:
                hrd[f"low_delay_hrd_flag[i={i}]"] = reader.read_bit()
            
            # NAL HRD parameters
            if hrd.get("nal_hrd_parameters_present_flag", False):
                hrd[f"nal_cpb_cnt_minus1[i={i}]"] = 0
                if not hrd[f"low_delay_hrd_flag[i={i}]"]:
                    hrd[f"nal_cpb_cnt_minus1[i={i}]"] = reader.read_ue()
                
                for j in range(hrd[f"nal_cpb_cnt_minus1[i={i}"] + 1):
                    hrd[f"nal_bit_rate_value_minus1[i={i}][j={j}]"] = reader.read_ue()
                    hrd[f"nal_cpb_size_value_minus1[i={i}][j={j}]"] = reader.read_ue()
                    hrd[f"nal_cbr_flag[i={i}][j={j}]"] = reader.read_bit()
            
            # VCL HRD parameters
            if hrd.get("vcl_hrd_parameters_present_flag", False):
                hrd[f"vcl_cpb_cnt_minus1[i={i}]"] = 0
                if not hrd[f"low_delay_hrd_flag[i={i}]"]:
                    hrd[f"vcl_cpb_cnt_minus1[i={i}]"] = reader.read_ue()
                
                for j in range(hrd[f"vcl_cpb_cnt_minus1[i={i}"] + 1):
                    hrd[f"vcl_bit_rate_value_minus1[i={i}][j={j}]"] = reader.read_ue()
                    hrd[f"vcl_cpb_size_value_minus1[i={i}][j={j}]"] = reader.read_ue()
                    hrd[f"vcl_cbr_flag[i={i}][j={j}]"] = reader.read_bit()
        
        return hrd
        
    except Error as e:
        print(f"HRD parameters parsing error (bitstring): {str(e)}")
        import traceback
        traceback.print_exc()
        return {}
    except Exception as e:
        print(f"HRD parameters parsing error (general): {str(e)}")
        import traceback
        traceback.print_exc()
        return {}