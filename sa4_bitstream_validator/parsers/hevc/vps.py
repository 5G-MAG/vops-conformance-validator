"""
    Parsing of HEVC VPS.
"""

import math

from bitstring import Error

from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention
from ..inferred_value import InferredValue
from .ptl import parse_profile_tier_level
from .hrd_parameters import parse_hrd_parameters


class TrackedDict(dict):
    """Dictionary that tracks when items are added"""
    def __init__(self, owner, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._name = name

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if hasattr(self._owner, '_initialized') and self._owner._initialized:
            self._owner._initialized_vars.add(self._name)

    def __delitem__(self, key):
        super().__delitem__(key)


class TrackedList(list):
    """List that tracks when items are added"""
    def __init__(self, owner, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._name = name

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if hasattr(self._owner, '_initialized') and self._owner._initialized:
            self._owner._initialized_vars.add(self._name)

    def append(self, item):
        super().append(item)
        if hasattr(self._owner, '_initialized') and self._owner._initialized:
            self._owner._initialized_vars.add(self._name)

    def extend(self, iterable):
        super().extend(iterable)
        if hasattr(self._owner, '_initialized') and self._owner._initialized:
            self._owner._initialized_vars.add(self._name)

    def insert(self, index, item):
        super().insert(index, item)
        if hasattr(self._owner, '_initialized') and self._owner._initialized:
            self._owner._initialized_vars.add(self._name)


class VpsInternalVariables:
    """Class to store internal variables used during VPS parsing"""

    def __init__(self):
        # Track which variables have been initialized
        self._initialized_vars = set()

        # Layer-related variables
        self.MaxLayersMinus1 = 0
        self.NumScalabilityTypes = 0
        self.NumViews = 0
        self.NumIndependentLayers = 0
        self.NumLayerSets = 0
        self.NumOutputLayerSets = 0

        # Scalability-related variables
        self.ScalabilityId = TrackedDict(self, "ScalabilityId")  # [i][smIdx]
        self.DepthLayerFlag = TrackedDict(self, "DepthLayerFlag")  # [lId]
        self.ViewOrderIdx = TrackedDict(self, "ViewOrderIdx")    # [lId]
        self.DependencyId = TrackedDict(self, "DependencyId")    # [lId]
        self.AuxId = TrackedDict(self, "AuxId")           # [lId]

        # Dependency-related variables
        self.DependencyFlag = TrackedDict(self, "DependencyFlag")  # [i][j]
        self.NumDirectRefLayers = TrackedDict(self, "NumDirectRefLayers")  # [lId]
        self.IdDirectRefLayer = TrackedDict(self, "IdDirectRefLayer")    # [lId][d]
        self.NumRefLayers = TrackedDict(self, "NumRefLayers")        # [lId]
        self.IdRefLayer = TrackedDict(self, "IdRefLayer")          # [lId][r]
        self.NumPredictedLayers = TrackedDict(self, "NumPredictedLayers")  # [lId]
        self.IdPredictedLayer = TrackedDict(self, "IdPredictedLayer")    # [lId][p]

        # Tree partition variables
        self.TreePartitionLayerIdList = TrackedDict(self, "TreePartitionLayerIdList")  # [k][j]
        self.NumLayersInTreePartition = TrackedDict(self, "NumLayersInTreePartition")  # [k]
        self.layerIdInListFlag = TrackedList(self, "layerIdInListFlag")  # [lId]

        # Layer set variables
        self.NumLayersInIdList = TrackedList(self, "NumLayersInIdList")  # [lsIdx]
        self.LayerSetLayerIdList = TrackedList(self, "LayerSetLayerIdList")  # [lsIdx][j]
        self.OlsIdxToLsIdx = TrackedList(self, "OlsIdxToLsIdx")  # [olsIdx]
        self.MaxSubLayersInLayerSetMinus1 = TrackedList(self, "MaxSubLayersInLayerSetMinus1")  # [lsIdx]

        # Mark that initialization is complete
        self._initialized = True

    def __setattr__(self, name, value):
        """Override __setattr__ to track which variables have been initialized"""
        if hasattr(self, '_initialized') and self._initialized and not name.startswith('_'):
            self._initialized_vars.add(name)
        super().__setattr__(name, value)

    def to_dict(self):
        """Convert internal variables to a dictionary with _ prefix"""
        result = {}
        for attr_name in dir(self):
            if not attr_name.startswith('_') and not callable(getattr(self, attr_name)):
                # Only include variables that have been initialized
                if attr_name not in self._initialized_vars:
                    continue
                value = getattr(self, attr_name)
                if isinstance(value, dict):
                    for key, val in value.items():
                        if isinstance(key, tuple):
                            if attr_name == "LayerSetLayerIdList":
                                key_str = f"[i={key[0]}][j={key[1]}]"
                            elif attr_name == "ScalabilityId":
                                key_str = f"[i={key[0]}][j={key[1]}]"
                            elif attr_name == "DependencyFlag":
                                key_str = f"[i={key[0]}][j={key[1]}]"
                            elif attr_name == "IdDirectRefLayer":
                                key_str = f"[i={key[0]}][j={key[1]}]"
                            elif attr_name == "IdRefLayer":
                                key_str = f"[i={key[0]}][j={key[1]}]"
                            elif attr_name == "IdPredictedLayer":
                                key_str = f"[i={key[0]}][j={key[1]}]"
                            elif attr_name == "TreePartitionLayerIdList":
                                key_str = f"[i={key[0]}][j={key[1]}]"
                            else:
                                key_str = ''.join(f"[{i}={k}]" for i, k in enumerate(key))
                            result[f"_{attr_name}{key_str}"] = val
                        else:
                            result[f"_{attr_name}[i={key}]"] = val
                elif isinstance(value, list):
                    for idx, val in enumerate(value):
                        if isinstance(val, list):
                            for jdx, val2 in enumerate(val):
                                result[f"_{attr_name}[i={idx}][j={jdx}]"] = val2
                        else:
                            result[f"_{attr_name}[i={idx}]"] = val
                else:
                    result[f"_{attr_name}"] = value
        return result


def parse_rep_format(reader, i):
    """Parse rep_format structure according to HEVC specification"""
    rep_format = {}

    rep_format[f"pic_width_vps_in_luma_samples"] = reader.read_bits(16)
    rep_format[f"pic_height_vps_in_luma_samples"] = reader.read_bits(16)
    rep_format[f"chroma_and_bit_depth_vps_present_flag"] = reader.read_bit()

    if rep_format[f"chroma_and_bit_depth_vps_present_flag"]:
        rep_format[f"chroma_format_vps_idc"] = reader.read_bits(2)

        if rep_format[f"chroma_format_vps_idc"] == 3:
            rep_format[f"separate_colour_plane_vps_flag"] = reader.read_bit()

        rep_format[f"bit_depth_vps_luma_minus8"] = reader.read_bits(4)
        rep_format[f"bit_depth_vps_chroma_minus8"] = reader.read_bits(4)

    rep_format[f"conformance_window_vps_flag"] = reader.read_bit()

    if rep_format[f"conformance_window_vps_flag"]:
        rep_format[f"conf_win_vps_left_offset"] = reader.read_ue()
        rep_format[f"conf_win_vps_right_offset"] = reader.read_ue()
        rep_format[f"conf_win_vps_top_offset"] = reader.read_ue()
        rep_format[f"conf_win_vps_bottom_offset"] = reader.read_ue()

    return rep_format


def parse_dpb_size(reader, vars, vps_base_layer_internal_flag, NecessaryLayerFlag):
    """Parse dpb_size structure"""
    dpb_size = {}

    for i in range(1, vars.NumOutputLayerSets):
        currLsIdx = vars.OlsIdxToLsIdx[i]
        dpb_size[f"sub_layer_flag_info_present_flag[i={i}]"] = reader.read_bit()

        for j in range(vars.MaxSubLayersInLayerSetMinus1[currLsIdx] + 1):
            if j == 0:
                dpb_size[f"sub_layer_dpb_info_present_flag[i={i}][j={j}]"] = InferredValue(True)
            elif j>0 and dpb_size[f"sub_layer_flag_info_present_flag[i={i}]"]:
                dpb_size[f"sub_layer_dpb_info_present_flag[i={i}][j={j}]"] = bool(reader.read_bit())
            if dpb_size[f"sub_layer_dpb_info_present_flag[i={i}][j={j}]"]:
                for k in range(vars.NumLayersInIdList[currLsIdx]):
                    if NecessaryLayerFlag[i][k] and (vps_base_layer_internal_flag or
                                                     ( vars.LayerSetLayerIdList[currLsIdx][k] != 0 )):
                        dpb_size[f"max_vps_dec_pic_buffering_minus1[i={i}][k={k}][j={j}]"] = reader.read_ue()

                dpb_size[f"max_vps_num_reorder_pics[i={i}][j={j}]"] = reader.read_ue()
                dpb_size[f"max_vps_latency_increase_plus1[i={i}][j={j}]"] = reader.read_ue()


    return dpb_size

def parse_vps(payload_data):
    """Parse Video Parameter Set from payload bytes"""
    # Remove emulation prevention bytes
    clean_data = remove_emulation_prevention(payload_data)
    if not clean_data:
        return None

    reader = BitReader(clean_data)

    # Initialize internal variables
    vars = VpsInternalVariables()

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

    ptl_result = parse_profile_tier_level(True, vps["vps_max_sub_layers_minus1"], reader)
    vps["profile_tier_level[i=0]"] = ptl_result

    vps["vps_sub_layer_ordering_info_present_flag"] = reader.read_bit()

    max_sub_layers = vps["vps_max_sub_layers_minus1"] + 1
    for i in range(vps["vps_sub_layer_ordering_info_present_flag"] and max_sub_layers or 1):
        vps[f"vps_max_dec_pic_buffering_minus1[i={i}]"] = reader.read_ue()
        vps[f"vps_max_num_reorder_pics[i={i}]"] = reader.read_ue()
        vps[f"vps_max_latency_increase_plus1[i={i}]"] = reader.read_ue()

    vps["vps_max_layer_id"] = reader.read_bits(6)

    vps["vps_num_layer_sets_minus1"] = reader.read_ue()

    for i in range(1, vps["vps_num_layer_sets_minus1"] + 1):
        for j in range(vps["vps_max_layer_id"] + 1):
            vps[f"layer_id_included_flag[i={i}][j={j}]"] = reader.read_bit()

    # Calculate internal variables
    vars.NumLayersInIdList = [0] * (vps["vps_num_layer_sets_minus1"] + 1)
    vars.LayerSetLayerIdList = [[] for _ in range(vps["vps_num_layer_sets_minus1"] + 1)]
    for i in range(1, vps["vps_num_layer_sets_minus1"] + 1):
        n = 0
        for j in range(vps["vps_max_layer_id"] + 1):
            if vps[f"layer_id_included_flag[i={i}][j={j}]"]:
                n = n+1
                vars.LayerSetLayerIdList[i].append(j)
        vars.NumLayersInIdList[i] = n

    vps["vps_timing_info_present_flag"] = reader.read_bit()

    if vps["vps_timing_info_present_flag"]:
        vps["vps_num_units_in_tick"] = reader.read_bits(32)
        vps["vps_time_scale"] = reader.read_bits(32)
        vps["vps_poc_proportional_to_timing_flag"] = reader.read_bit()

        if vps["vps_poc_proportional_to_timing_flag"]:
            vps["vps_num_ticks_poc_diff_one_minus1"] = reader.read_ue()

        vps["vps_num_hrd_parameters"] = reader.read_ue()

        for i in range(vps["vps_num_hrd_parameters"]):
            vps[f"hrd_layer_set_idx[i={i}]"] = reader.read_ue()

            if i > 0:
                vps[f"cprms_present_flag[i={i}]"] = reader.read_bit()
                cprms_present = vps[f"cprms_present_flag[i={i}]"]
            else:
                cprms_present = 1

        
            hrd_params = parse_hrd_parameters(
                cprms_present,
                vps["vps_max_sub_layers_minus1"], reader
            )

            for key, value in hrd_params.items():
                vps[f"{key}[i={i}]"] = value

    vps["vps_extension_flag"] = reader.read_bit()

    if vps["vps_extension_flag"]:
        reader.bitstream.bytealign()

        vps = parse_vps_extensions(reader, vps, vars)

        vps["vps_extension2_flag"] = reader.read_bit()

        if vps["vps_extension2_flag"]:
            # Parse vps_extension_data_flag for remaining bits
            while reader.bitstream.pos < len(reader.bitstream):
                vps["vps_extension_data_flag"] = reader.read_bit()

    # Copy internal variables to vps object with _ prefix
    vars_dict = vars.to_dict()
    for key, value in vars_dict.items():
        vps[key] = value

    return {k: v for k, v in vps.items() if v is not None}

def parse_vps_extensions(reader, vps, vars):
    """Parse VPS extension"""

    # Internal variables: MaxLayersMinus1
    vars.MaxLayersMinus1 = min(62, vps["vps_max_layers_minus1"])

    if vps["vps_max_layers_minus1"] > 0 and vps["vps_base_layer_internal_flag"]:
        ptl_result = parse_profile_tier_level(False, vps["vps_max_sub_layers_minus1"], reader)
        vps["profile_tier_level[i=1]"] = ptl_result

    vps["splitting_flag"] = reader.read_bit()

    # Internal variables: NumScalabilityTypes
    vars.NumScalabilityTypes = 0
    for i in range(16):
        vps[f"scalability_mask_flag[i={i}]"] = reader.read_bit()
        vars.NumScalabilityTypes += vps[f"scalability_mask_flag[i={i}]"]

    for j in range(vars.NumScalabilityTypes - vps["splitting_flag"]):
        vps[f"dimension_id_len_minus1[j={j}]"] = reader.read_bits(3)

    vps["vps_nuh_layer_id_present_flag"] = reader.read_bit()

    # layer_id_in_nuh[0] is always 0 (base layer)
    vps["layer_id_in_nuh[i=0]"] = InferredValue(0)

    for i in range(1, vars.MaxLayersMinus1 + 1):
        if vps["vps_nuh_layer_id_present_flag"]:
            vps[f"layer_id_in_nuh[i={i}]"] = reader.read_bits(6)
        else:
            vps[f"layer_id_in_nuh[i={i}]"] = i

        if not vps["splitting_flag"]:
            for j in range(vars.NumScalabilityTypes):
                dimension_id_len = vps[f"dimension_id_len_minus1[j={j}]"] + 1
                vps[f"dimension_id[i={i}][j={j}]"] = reader.read_bits(dimension_id_len)

    # Internal variables: ScalabilityId
    if not vps["splitting_flag"]:
        for i in range(vars.MaxLayersMinus1 + 1):  # i from 0 to max_layers_minus1
            j_index = 0
            for smIdx in range(16):  # smIdx from 0 to 15
                if vps.get(f"scalability_mask_flag[i={smIdx}]", 0):
                    # If scalability dimension is enabled, use the corresponding dimension_id
                    dimension_id_value = vps.get(f"dimension_id[i={i}][j={j_index}]", 0)
                    vars.ScalabilityId[(i, smIdx)] = dimension_id_value
                    j_index += 1
                else:
                    # If scalability dimension is disabled, set to 0
                    vars.ScalabilityId[(i, smIdx)] = 0

    # Internal variables: DepthLayerFlag, ViewOrderIdx, DependencyId, AuxId
    for i in range(vars.MaxLayersMinus1 + 1):
        lId = vps[f"layer_id_in_nuh[i={i}]"]

        vars.DepthLayerFlag[lId] = vars.ScalabilityId.get((i, 0), 0)
        vars.ViewOrderIdx[lId] = vars.ScalabilityId.get((i, 1), 0)
        vars.DependencyId[lId] = vars.ScalabilityId.get((i, 2), 0)
        vars.AuxId[lId] = vars.ScalabilityId.get((i, 3), 0)

    # Internal variables: NumViews
    vars.NumViews = 1
    for i in range(1, vars.MaxLayersMinus1 + 1):
        lId = vps[f"layer_id_in_nuh[i={i}]"]

        if i > 0:
            newViewFlag = 1
            for j in range(i):
                jLId = vps[f"layer_id_in_nuh[i={j}]"]
                if vars.ViewOrderIdx[lId] == vars.ViewOrderIdx[jLId]:
                    newViewFlag = 0
            vars.NumViews += newViewFlag

    vps["view_id_len"] = reader.read_bits(4)
    if vps["view_id_len"] > 0:
        for i in range(vars.NumViews):
            vps[f"view_id_val[i={i}]"] = reader.read_bits(vps["view_id_len"])

    for i in range(1, vars.MaxLayersMinus1 + 1):
        for j in range(i):
            vps[f"direct_dependency_flag[i={i}][j={j}]"] = reader.read_bit()

    # Internal variables: DependencyFlag
    for i in range(vars.MaxLayersMinus1 + 1):
        for j in range(vars.MaxLayersMinus1 + 1):
            # Initialize with direct_dependency_flag
            if i > j:
                vars.DependencyFlag[(i, j)] = vps.get(f"direct_dependency_flag[i={i}][j={j}]", 0)
            elif i == j:
                vars.DependencyFlag[(i, j)] = 0
            else:  # i < j
                vars.DependencyFlag[(i, j)] = 0

            # Check transitive dependencies
            for k in range(i):
                if (vps.get(f"direct_dependency_flag[i={i}][j={k}]", 0) and
                    vars.DependencyFlag.get((k, j), 0)):
                    vars.DependencyFlag[(i, j)] = 1

    # Internal variables: NumDirectRefLayers, IdDirectRefLayer, NumRefLayers, IdRefLayer,
    # NumPredictedLayers, IdPredictedLayer
    for i in range(vars.MaxLayersMinus1 + 1):
        iNuhLId = vps[f"layer_id_in_nuh[i={i}]"]
        d = 0
        r = 0
        p = 0

        for j in range(vars.MaxLayersMinus1 + 1):
            jNuhLid = vps[f"layer_id_in_nuh[i={j}]"]

            # IdDirectRefLayer
            if vps.get(f"direct_dependency_flag[i={i}][j={j}]", 0):
                vars.IdDirectRefLayer[(iNuhLId, d)] = jNuhLid
                d += 1

            # IdRefLayer
            if vars.DependencyFlag.get((i, j), 0):
                vars.IdRefLayer[(iNuhLId, r)] = jNuhLid
                r += 1

            # IdPredictedLayer
            if vars.DependencyFlag.get((j, i), 0):
                vars.IdPredictedLayer[(iNuhLId, p)] = jNuhLid
                p += 1

        vars.NumDirectRefLayers[iNuhLId] = d
        vars.NumRefLayers[iNuhLId] = r
        vars.NumPredictedLayers[iNuhLId] = p

    # Internal variables: NumIndependentLayers, NumLayersInTreePartition, TreePartitionLayerIdList
    vars.layerIdInListFlag = [0] * 64

    k = 0
    for i in range(vars.MaxLayersMinus1 + 1):
        iNuhLId = vps[f"layer_id_in_nuh[i={i}]"]

        if vars.NumDirectRefLayers.get(iNuhLId, 0) == 0:
            vars.TreePartitionLayerIdList[(k, 0)] = iNuhLId
            h = 1

            for j in range(vars.NumPredictedLayers.get(iNuhLId, 0)):
                predLId = vars.IdPredictedLayer.get((iNuhLId, j), 0)

                if not vars.layerIdInListFlag[predLId]:
                    h += 1
                    vars.TreePartitionLayerIdList[(k, h)] = predLId
                    vars.layerIdInListFlag[predLId] = 1

            k += 1
            vars.NumLayersInTreePartition[k] = h

    vars.NumIndependentLayers = k

    if vars.NumIndependentLayers > 1:
        vps["num_add_layer_sets"] = reader.read_ue()
    else:
        vps["num_add_layer_sets"] = InferredValue(0)

    for i in range(int(vps["num_add_layer_sets"])):
        for j in range(1, vars.NumIndependentLayers):
            num_layers = vars.NumLayersInTreePartition.get(j, 0)
            bit_length = math.ceil(math.log2(num_layers + 1))
            vps[f"highest_layer_idx_plus1[i={i}][j={j}]"] = reader.read_bits(bit_length)

    vps["vps_sub_layers_max_minus1_present_flag"] = reader.read_bit()

    if vps["vps_sub_layers_max_minus1_present_flag"]:
        for i in range(vars.MaxLayersMinus1 + 1):
            vps[f"sub_layers_vps_max_minus1[i={i}]"] = reader.read_bits(3)
    
    vps["max_tid_ref_present_flag"] = reader.read_bit()

    if vps["max_tid_ref_present_flag"]:
        for i in range(vars.MaxLayersMinus1):
            for j in range(i + 1, vars.MaxLayersMinus1 + 1):
                if vps.get(f"direct_dependency_flag[i={j}][j={i}]", 0):
                    vps[f"max_tid_il_ref_pics_plus1[i={i}][j={j}]"] = reader.read_bits(3)

    vps["default_ref_layers_active_flag"] = reader.read_bit()

    vps["vps_num_profile_tier_level_minus1"] = reader.read_ue()

    start_idx = 2 if vps["vps_base_layer_internal_flag"] else 1

    for i in range(start_idx, vps["vps_num_profile_tier_level_minus1"] + 1):
        vps[f"vps_profile_present_flag[i={i}]"] = reader.read_bit()
        ptl_result = parse_profile_tier_level(
            vps[f"vps_profile_present_flag[i={i}]"],
            vps["vps_max_sub_layers_minus1"],
            reader
        )
        vps[f"profile_tier_level[i={i}]"] = ptl_result

    vars.NumLayerSets = vps["vps_num_layer_sets_minus1"] + 1 + int(vps["num_add_layer_sets"])

    if vars.NumLayerSets > 1:
        vps["num_add_olss"] = reader.read_ue()
        vps["default_output_layer_idc"] = reader.read_bits(2)

    vars.NumOutputLayerSets = vps["num_add_olss"] + vars.NumLayerSets

    vars.OlsIdxToLsIdx = list(range(vars.NumLayerSets))
    for i in range(vars.NumLayerSets, vars.NumOutputLayerSets):
        vars.OlsIdxToLsIdx.append(vps.get(f"layer_set_idx_for_ols_minus1[i={i}]", 0) + 1)

    for i in range(1, vars.NumOutputLayerSets):
        if vars.NumLayerSets > 2 and i >= vars.NumLayerSets:
            length_layer_set_idx = math.ceil(math.log2(vars.NumLayerSets - 1))
            vps[f"layer_set_idx_for_ols_minus1[i={i}]"] = reader.read_bits(length_layer_set_idx)

        if i > vars.MaxLayersMinus1 or vps["default_output_layer_idc"] == 2:
            for j in range(vars.NumLayersInIdList[vars.OlsIdxToLsIdx[i]]):
                vps[f"output_layer_flag[i={i}][j={j}]"] = reader.read_bit()

        for j in range(vars.MaxLayersMinus1 + 1):
            length_ptl_idx = math.ceil(math.log2(vps["vps_num_profile_tier_level_minus1"] + 1))
            vps[f"profile_tier_level_idx[i={i}][j={j}]"] = reader.read_bits(length_ptl_idx)

    vps["vps_num_rep_formats_minus1"] = reader.read_ue()

    for i in range(vps["vps_num_rep_formats_minus1"] + 1):
        rep_format_result = parse_rep_format(reader, i)
        vps[f"rep_format[i={i}]"] = rep_format_result

    if vps["vps_num_rep_formats_minus1"] > 0 and reader.bitstream.pos < len(reader.bitstream):
        vps["rep_format_idx_present_flag"] = reader.read_bit()

        if vps["rep_format_idx_present_flag"] and reader.bitstream.pos < len(reader.bitstream):
            start_idx = 1 if vps["vps_base_layer_internal_flag"] else 0
            for i in range(start_idx, vars.MaxLayersMinus1 + 1):
                vps[f"vps_rep_format_idx[i={i}]"] = reader.read_ue()

    vps["max_one_active_ref_layer_flag"] = reader.read_bit()

    vps["vps_poc_lsb_aligned_flag"] = reader.read_bit()

    for i in range(1, vars.MaxLayersMinus1 + 1):
        if vars.NumDirectRefLayers[vps[f"layer_id_in_nuh[i={i}]"]] == 0:
            vps[f"poc_lsb_not_present_flag[i={i}]"] = reader.read_bit()

    # Calculate MaxSubLayersInLayerSetMinus1
    vars.MaxSubLayersInLayerSetMinus1 = [0] * vars.NumLayerSets
    for i in range(vars.NumLayerSets):
        vars.MaxSubLayersInLayerSetMinus1[i] = vps["vps_max_sub_layers_minus1"]

    # Calculate NecessaryLayerFlag
    NecessaryLayerFlag = [[0] * vars.NumLayersInIdList[i] for i in range(vars.NumLayerSets)]
    for i in range(vars.NumLayerSets):
        for j in range(vars.NumLayersInIdList[i]):
            NecessaryLayerFlag[i][j] = 1  # Simplified - all layers are necessary

    vps.update(parse_dpb_size(reader, vars, vps["vps_base_layer_internal_flag"], NecessaryLayerFlag))

    vps["direct_dep_type_len_minus2"] = reader.read_ue()

    vps["direct_dependency_all_layers_flag"] = reader.read_bit()

    if vps["direct_dependency_all_layers_flag"] and reader.bitstream.pos < len(reader.bitstream):
        vps["direct_dependency_all_layers_type"] = reader.read_bits(
            vps["direct_dep_type_len_minus2"] + 2
        )
    elif reader.bitstream.pos < len(reader.bitstream):
        start_i = 1 if vps["vps_base_layer_internal_flag"] else 2
        start_j = 0 if vps["vps_base_layer_internal_flag"] else 1

        for i in range(start_i, vars.MaxLayersMinus1 + 1):
            for j in range(start_j, i):
                if vps.get(f"direct_dependency_flag[i={i}][j={j}]", 0):
                    vps[f"direct_dependency_type[i={i}][j={j}]"] = reader.read_bits(
                        vps["direct_dep_type_len_minus2"] + 2
                        )

    vps["vps_non_vui_extension_length"] = reader.read_ue()

    for i in range(1, vps["vps_non_vui_extension_length"] + 1):
        vps[f"vps_non_vui_extension_data_byte[i={i}]"] = reader.read_bits(8)

    vps["vps_vui_present_flag"] = reader.read_bit()

    if vps["vps_vui_present_flag"] and reader.bitstream.pos < len(reader.bitstream):
        reader.bitstream.bytealign()


    return vps