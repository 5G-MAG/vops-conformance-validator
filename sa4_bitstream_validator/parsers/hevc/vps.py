"""
    Parsing of HEVC VPS.
"""

from bitstring import Error

from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention
from .ptl import parse_profile_tier_level
from .hrd_parameters import parse_vps_hrd_parameters

def parse_vps(payload_data):
    """Parse Video Parameter Set from payload bytes"""
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(payload_data)
        if not clean_data:
            return None

        reader = BitReader(clean_data)

        # Parse basic VPS parameters
        vps = {
            "vps_video_parameter_set_id": reader.read_bits(4),
            "vps_base_layer_internal_flag": reader.read_bit(),
            "vps_base_layer_available_flag": reader.read_bit(),
            "vps_max_layers_minus1": reader.read_bits(6),
            "vps_max_sub_layers_minus1": reader.read_bits(3),
            "vps_temporal_id_nesting_flag": reader.read_bit(),
            "vps_reserved_0xffff_16bits": reader.read_bits(16)
        }
        
        # Parse profile tier level
        vps.update(parse_profile_tier_level(True, vps["vps_max_sub_layers_minus1"], reader))
        
        # Parse VPS sub-layer ordering info present flag
        vps["vps_sub_layer_ordering_info_present_flag"] = reader.read_bit()
        
        # Parse sub-layer ordering information
        max_sub_layers = vps["vps_max_sub_layers_minus1"] + 1
        for i in range(vps["vps_sub_layer_ordering_info_present_flag"] and max_sub_layers or 1):
            vps[f"vps_max_dec_pic_buffering_minus1[i={i}]"] = reader.read_ue()
            vps[f"vps_max_num_reorder_pics[i={i}]"] = reader.read_ue()
            vps[f"vps_max_latency_increase_plus1[i={i}]"] = reader.read_ue()
        
        # Parse max layer ID
        vps["vps_max_layer_id"] = reader.read_bits(6)
        
        # Parse vps_num_layer_sets_minus1
        vps["vps_num_layer_sets_minus1"] = reader.read_ue()
        
        # Parse layer ID included flags for each layer set
        for i in range(1, vps["vps_num_layer_sets_minus1"] + 1):
            for j in range(vps["vps_max_layer_id"] + 1):
                vps[f"layer_id_included_flag[i={i}][j={j}]"] = reader.read_bit()
        
        # Parse timing info
        vps["vps_timing_info_present_flag"] = reader.read_bit()
        
        if vps["vps_timing_info_present_flag"]:
            vps["vps_num_units_in_tick"] = reader.read_bits(32)
            vps["vps_time_scale"] = reader.read_bits(32)
            vps["vps_poc_proportional_to_timing_flag"] = reader.read_bit()
            
            if vps["vps_poc_proportional_to_timing_flag"]:
                vps["vps_num_ticks_poc_diff_one_minus1"] = reader.read_ue()
            
            vps["vps_num_hrd_parameters"] = reader.read_ue()
            
            # Parse HRD parameters
            for i in range(vps["vps_num_hrd_parameters"]):
                vps[f"hrd_layer_set_idx[i={i}]"] = reader.read_ue()
                
                if i > 0:
                    vps[f"cprms_present_flag[i={i}]"] = reader.read_bit()
                    cprms_present = vps[f"cprms_present_flag[i={i}]"]
                else:
                    cprms_present = 1
                
                # Parse full HRD parameters using the new module
                max_sub_layers_minus1 = vps["vps_max_sub_layers_minus1"]
                
                # Parse HRD parameters and flatten them into the main VPS object
                hrd_params = parse_vps_hrd_parameters(
                    cprms_present, max_sub_layers_minus1, reader
                )

                for key, value in hrd_params.items():
                    vps[f"{key}[i={i}]"] = value
        
        # Parse VPS extension flag
        vps["vps_extension_flag"] = reader.read_bit()

        if vps["vps_extension_flag"]:            
            reader.bitstream.bytealign()
            
            vps = parse_vps_extensions(reader, vps)
            
            # Parse VPS extension2 flag
            vps["vps_extension2_flag"] = reader.read_bit()
            
            if vps["vps_extension2_flag"]:
                # Parse vps_extension_data_flag for remaining bits
                while reader.bitstream.pos < len(reader.bitstream):
                    vps["vps_extension_data_flag"] = reader.read_bit()      
        
        return {k: v for k, v in vps.items() if v is not None}

    except Error as e:
        print(f"VPS parsing error (bitstring): {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"VPS parsing error (general): {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def parse_vps_extensions(reader, vps):
    """Parse VPS extension"""
    if vps["vps_max_layers_minus1"] > 0 and vps["vps_base_layer_internal_flag"]:
        vps.update(parse_profile_tier_level(False, vps["vps_max_sub_layers_minus1"], reader))

    vps["splitting_flag"] = reader.read_bit()
    
    num_scalability_types = 0
    for i in range(16):
        vps[f"scalability_mask_flag[i={i}]"] = reader.read_bit()
        num_scalability_types += vps[f"scalability_mask_flag[i={i}]"]
    
    for j in range(num_scalability_types - vps["splitting_flag"]):
        vps[f"dimension_id_len_minus1[j={j}]"] = reader.read_bits(3)
    
    vps["vps_nuh_layer_id_present_flag"] = reader.read_bit()
    
    max_layers_minus1 = min(62, vps["vps_max_layers_minus1"])
    for i in range(1, max_layers_minus1 + 1):
        if vps["vps_nuh_layer_id_present_flag"]:
            vps[f"layer_id_in_nuh[i={i}]"] = reader.read_bits(6)
        
        if not vps["splitting_flag"]:
            for j in range(num_scalability_types):
                vps[f"dimension_id[i={i}][j={j}]"] = reader.read_bits(vps[f"dimension_id_len_minus1[j={j}]"]+1)
    
    vps["view_id_len"] = reader.read_bits(4)
    
    # Parse view ID values
    num_views = 0  # This should be derived from other parameters
    if vps["view_id_len"] > 0:
        for i in range(num_views):
            vps["view_id_val[i={i}]"] = reader.read_bits(vps["view_id_len"])
        
    return vps