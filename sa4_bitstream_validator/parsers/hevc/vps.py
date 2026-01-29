"""
    Parsing of HEVC VPS.
"""

from bitstring import Error

from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention
from .ptl import parse_profile_tier_level
from .hrd_parameters import parse_hrd_parameters

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
                hrd_params = parse_hrd_parameters(
                    cprms_present, max_sub_layers_minus1, reader
                )

                for key, value in hrd_params.items():
                    vps[f"{key}[i={i}]"] = value

        # Parse VPS extension flag
        vps["vps_extension_flag"] = reader.read_bit()

        if vps["vps_extension_flag"]:
            reader.bitstream.bytealign()

            vps = parse_vps_extensions(reader, vps)

            # Parse VPS extension2 flag if bits are available
            if reader.bitstream.pos < len(reader.bitstream):
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
    """Parse VPS extension according to HEVC specification Annex F.7.3.2.1.1"""

    # Parse profile_tier_level if conditions are met
    if vps["vps_max_layers_minus1"] > 0 and vps["vps_base_layer_internal_flag"]:
        ptl_result = parse_profile_tier_level(False, vps["vps_max_sub_layers_minus1"], reader)
        vps.update(ptl_result)

    # Parse splitting_flag
    vps["splitting_flag"] = reader.read_bit()

    # Parse scalability_mask_flag and calculate NumScalabilityTypes
    _NumScalabilityTypes = 0
    for i in range(16):
        vps[f"scalability_mask_flag[i={i}]"] = reader.read_bit()
        _NumScalabilityTypes += vps[f"scalability_mask_flag[i={i}]"]

    vps["_NumScalabilityTypes"] = _NumScalabilityTypes

    # Parse dimension_id_len_minus1
    for j in range(_NumScalabilityTypes - vps["splitting_flag"]):
        vps[f"dimension_id_len_minus1[j={j}]"] = reader.read_bits(3)

    # Parse vps_nuh_layer_id_present_flag
    vps["vps_nuh_layer_id_present_flag"] = reader.read_bit()

    max_layers_minus1 = min(62, vps["vps_max_layers_minus1"])
    vps["_NumLayerSets"] = max_layers_minus1 + 1
    vps["_NumIndependentLayers"] = max_layers_minus1 + 1
    vps["_NumLayersInIdList"] = max_layers_minus1 + 1

    # Parse layer_id_in_nuh and dimension_id
    for i in range(1, max_layers_minus1 + 1):
        if vps["vps_nuh_layer_id_present_flag"]:
            vps[f"layer_id_in_nuh[i={i}]"] = reader.read_bits(6)

        if not vps["splitting_flag"]:
            j_index = 0
            for smIdx in range(16):
                if vps.get(f"scalability_mask_flag[i={smIdx}]", 0):
                    dimension_id_len = vps[f"dimension_id_len_minus1[j={j_index}]"] + 1
                    vps[f"dimension_id[i={i}][j={j_index}]"] = reader.read_bits(dimension_id_len)
                    j_index += 1

    # Calculate ScalabilityId for each layer according to HEVC spec F.7.3.2.1.1
    if not vps["splitting_flag"]:
        for i in range(max_layers_minus1 + 1):  # i from 0 to max_layers_minus1
            j_index = 0
            for smIdx in range(16):  # smIdx from 0 to 15
                if vps.get(f"scalability_mask_flag[i={smIdx}]", 0):
                    # If scalability dimension is enabled, use the corresponding dimension_id
                    dimension_id_value = vps.get(f"dimension_id[i={i}][j={j_index}]", 0)
                    vps[f"_ScalabilityId[i={i}][smIdx={smIdx}]"] = dimension_id_value
                    j_index += 1
                else:
                    # If scalability dimension is disabled, set to 0
                    vps[f"_ScalabilityId[i={i}][smIdx={smIdx}]"] = 0

    # Parse view_id_len
    vps["view_id_len"] = reader.read_bits(4)

    # Calculate NumViews based on view_id_len
    _NumViews = 0
    if vps["view_id_len"] > 0:
        # Parse view_id_val for all views
        for i in range(16):  # Maximum reasonable number of views
            vps[f"view_id_val[i={i}]"] = reader.read_bits(vps["view_id_len"])
            _NumViews += 1

    vps["_NumViews"] = _NumViews

    # Parse direct_dependency_flag
    for i in range(1, max_layers_minus1 + 1):
        for j in range(i):
            vps[f"direct_dependency_flag[i={i}][j={j}]"] = reader.read_bit()

    # Parse num_add_layer_sets
    if max_layers_minus1 > 0:  # NumIndependentLayers > 1
        vps["num_add_layer_sets"] = reader.read_ue()

        # Parse highest_layer_idx_plus1
        for i in range(vps["num_add_layer_sets"]):
            for j in range(1, max_layers_minus1):  # NumIndependentLayers - 1
                vps[f"highest_layer_idx_plus1[i={i}][j={j}]"] = reader.read_ue()

    # Parse vps_sub_layers_max_minus1_present_flag
    vps["vps_sub_layers_max_minus1_present_flag"] = reader.read_bit()

    if vps["vps_sub_layers_max_minus1_present_flag"]:
        for i in range(max_layers_minus1 + 1):
            vps[f"sub_layers_vps_max_minus1[i={i}]"] = reader.read_bits(3)

    # Parse max_tid_ref_present_flag
    vps["max_tid_ref_present_flag"] = reader.read_bit()

    if vps["max_tid_ref_present_flag"]:
        for i in range(max_layers_minus1):
            for j in range(i + 1, max_layers_minus1 + 1):
                if vps.get(f"direct_dependency_flag[i={j}][j={i}]", 0):
                    vps[f"max_tid_il_ref_pics_plus1[i={i}][j={j}]"] = reader.read_bits(3)

    # Parse default_ref_layers_active_flag
    vps["default_ref_layers_active_flag"] = reader.read_bit()

    # Parse vps_num_profile_tier_level_minus1
    vps["vps_num_profile_tier_level_minus1"] = reader.read_ue()

    # Parse additional profile_tier_level structures
    start_idx = 2 if vps["vps_base_layer_internal_flag"] else 1
    for i in range(start_idx, vps["vps_num_profile_tier_level_minus1"] + 1):
        # Check if we have bits left to read
        if reader.bitstream.pos >= len(reader.bitstream):
            break
        vps[f"vps_profile_present_flag[i={i}]"] = reader.read_bit()
        ptl_result = parse_profile_tier_level(
            vps[f"vps_profile_present_flag[i={i}]"],
            vps["vps_max_sub_layers_minus1"],
            reader
        )
        vps.update(ptl_result)

    # Parse output layer set information
    if max_layers_minus1 > 0:  # NumLayerSets > 1
        # Check if we have bits left to read
        if reader.bitstream.pos >= len(reader.bitstream):
            return vps

        vps["num_add_olss"] = reader.read_ue()

        # Check if we have bits left to read
        if reader.bitstream.pos >= len(reader.bitstream):
            return vps

        vps["default_output_layer_idc"] = reader.read_bits(2)

        # Calculate NumOutputLayerSets
        _NumOutputLayerSets = vps["num_add_olss"] + (max_layers_minus1 + 1)
        vps["_NumOutputLayerSets"] = _NumOutputLayerSets

        # Parse output layer set flags
        for i in range(1, _NumOutputLayerSets):
            # Check if we have bits left to read
            if reader.bitstream.pos >= len(reader.bitstream):
                break

            if max_layers_minus1 > 1 and i >= (max_layers_minus1 + 1):
                vps[f"layer_set_idx_for_ols_minus1[i={i}]"] = reader.read_ue()

            if i > max_layers_minus1 or vps["default_output_layer_idc"] == 2:
                for j in range(max_layers_minus1 + 1):  # NumLayersInIdList
                    # Check if we have bits left to read
                    if reader.bitstream.pos >= len(reader.bitstream):
                        break
                    vps[f"output_layer_flag[i={i}][j={j}]"] = reader.read_bit()

            # Parse profile_tier_level_idx
            for j in range(max_layers_minus1 + 1):
                # Check if we have bits left to read
                if reader.bitstream.pos >= len(reader.bitstream):
                    break
                vps[f"profile_tier_level_idx[i={i}][j={j}]"] = reader.read_ue()

            # Parse alt_output_layer_flag
            if reader.bitstream.pos >= len(reader.bitstream):
                break
            vps[f"alt_output_layer_flag[i={i}]"] = reader.read_bit()

    return vps