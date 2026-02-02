"""
    Parsers of HEVC bitstreams.
"""

import re
import binascii
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from sa4_bitstream_validator.parsers.base_parser import BaseParser
from sa4_bitstream_validator.parsers.hevc import parse_sps
from sa4_bitstream_validator.parsers.hevc import parse_vps
from sa4_bitstream_validator.tools import find_start_codes


def extract_parameter_value(value):
    """Extract actual value and inferred flag from ParsedValue object or regular value"""
    is_inferred = False
    actual_value = value
    if hasattr(value, 'inferred') and hasattr(value, 'value'):
        is_inferred = value.inferred
        # Keep the InferredValue object so it can handle its own string conversion
        actual_value = value
    return actual_value, is_inferred


def create_indexed_element(parent_elem, xml_key, actual_value, is_inferred=False):
    """Create XML element for indexed parameters like field[k={k}][j={j}]"""
    match_new_format = re.match(r"^([^\[]+?)((?:\[[^=]+=\d+\])+)$", xml_key)
    if match_new_format:
        base_key = match_new_format.group(1)
        index_parts = match_new_format.group(2)
        var_value_pairs = re.findall(r"\[([^=]+)=(\d+)\]", index_parts)

        elem = SubElement(parent_elem, base_key)
        for var_name, var_value in var_value_pairs:
            elem.set(var_name, var_value)
        if is_inferred:
            elem.set("inferred", "true")

        # Handle InferredValue objects - they handle their own string conversion
        elem.text = str(actual_value)
        return elem
    return None


def create_regular_element(parent_elem, xml_key, actual_value, is_inferred=False):
    """Create XML element for regular (non-indexed) parameters"""
    elem = SubElement(parent_elem, xml_key)
    if is_inferred:
        elem.set("inferred", "true")

    # Handle InferredValue objects - they handle their own string conversion
    elem.text = str(actual_value)
    return elem


def create_profile_tier_level_element(parent_elem, xml_key, actual_value, is_inferred=False):
    """Create XML element for nested profile_tier_level objects"""
    match_nested = re.match(r"^profile_tier_level\[i=(\d+)\]$", xml_key)
    if match_nested:
        i_value = match_nested.group(1)

        if isinstance(actual_value, dict):
            # Create the profile_tier_level element with index i
            ptl_elem = SubElement(parent_elem, "profile_tier_level")
            ptl_elem.set("i", i_value)

            # Add all PTL parameters as child elements
            for key, value in actual_value.items():
                ptl_actual_value, ptl_is_inferred = extract_parameter_value(value)

                # Try indexed parameter first, then fall back to regular
                indexed_elem = create_indexed_element(ptl_elem, key, ptl_actual_value, ptl_is_inferred)
                if indexed_elem is None:
                    create_regular_element(ptl_elem, key, ptl_actual_value, ptl_is_inferred)
            return ptl_elem
        else:
            # If actual_value is not a dict, treat it as a regular parameter
            return create_regular_element(parent_elem, xml_key, actual_value, is_inferred)
    return None


def create_rep_format_element(parent_elem, xml_key, actual_value, is_inferred=False):
    """Create XML element for nested rep_format objects"""
    match_nested = re.match(r"^rep_format\[i=(\d+)\]$", xml_key)
    if match_nested:
        i_value = match_nested.group(1)

        if isinstance(actual_value, dict):
            # Create the rep_format element with index i
            rep_format_elem = SubElement(parent_elem, "rep_format")
            rep_format_elem.set("i", i_value)

            # Add all rep_format parameters as child elements
            for key, value in actual_value.items():
                rep_actual_value, rep_is_inferred = extract_parameter_value(value)

                # Try indexed parameter first, then fall back to regular
                indexed_elem = create_indexed_element(rep_format_elem, key, rep_actual_value, rep_is_inferred)
                if indexed_elem is None:
                    create_regular_element(rep_format_elem, key, rep_actual_value, rep_is_inferred)
            return rep_format_elem
        else:
            # If actual_value is not a dict, treat it as a regular parameter
            return create_regular_element(parent_elem, xml_key, actual_value, is_inferred)
    return None


def process_parameters(parent_elem, parameters, include_internal_vars=False):
    """Process parameters and create corresponding XML elements"""
    internal_vars = []

    for key, value in parameters.items():
        # Skip internal variables if not requested
        if not include_internal_vars and key.startswith("_"):
            continue

        # Remove underscore prefix from internal variables when including them
        xml_key = key[1:] if key.startswith("_") and include_internal_vars else key

        # Handle internal variables by collecting them for later
        if key.startswith("_") and include_internal_vars:
            internal_vars.append((xml_key, value))
        else:
            actual_value, is_inferred = extract_parameter_value(value)

            # Try profile_tier_level first, then rep_format, then indexed, then regular
            ptl_elem = create_profile_tier_level_element(parent_elem, xml_key, actual_value, is_inferred)
            if ptl_elem is not None:
                continue

            rep_format_elem = create_rep_format_element(parent_elem, xml_key, actual_value, is_inferred)
            if rep_format_elem is not None:
                continue

            indexed_elem = create_indexed_element(parent_elem, xml_key, actual_value, is_inferred)
            if indexed_elem is None:
                create_regular_element(parent_elem, xml_key, actual_value, is_inferred)

    return internal_vars


def create_internal_variables_element(parent_elem, internal_vars):
    """Create InternalVariables element with collected internal variables"""
    if internal_vars:
        internal_vars_elem = SubElement(parent_elem, "InternalVariables")
        for xml_key, value in internal_vars:
            actual_value, _ = extract_parameter_value(value)

            # Try indexed parameter first, then fall back to regular
            indexed_elem = create_indexed_element(internal_vars_elem, xml_key, actual_value)
            if indexed_elem is None:
                create_regular_element(internal_vars_elem, xml_key, actual_value)


class HEVCParser(BaseParser):
    """Parser of HEVC bitstreams."""
    def bitstream_to_xml(self, bitstream, description, include_internal_vars=False):
        "Parse a HEVC bitstream"
        data = bitstream.read()
        start_codes = find_start_codes(data)
        if not start_codes:
            print("Error: No NAL units found in bitstream")
            return

        # Create XML root element with namespaces
        root = Element("HEVCBitstream")
        root.set("uri", bitstream.name)

        for i in range(len(start_codes)):
            start_pos, start_len = start_codes[i]

            # Determine NAL unit boundaries
            if i < len(start_codes) - 1:
                next_start, _ = start_codes[i+1]
                end_pos = next_start
            else:
                end_pos = len(data)

            # Extract start code
            start_code_hex = binascii.hexlify(data[start_pos:start_pos+start_len]).decode().upper()

            # Process NAL unit header
            header_start = start_pos + start_len
            if header_start + 2 > end_pos:
                continue  # Skip incomplete headers

            header_bytes = data[header_start:header_start+2]
            try:
                fzb, nut, nli, tid = self.parse_nal_header(header_bytes)
            except ValueError:
                continue

            # Calculate payload range
            payload_start = header_start + 2
            payload_length = end_pos - payload_start

            # Create XML elements
            nal_unit = SubElement(root, "NALUnit")

            sc = SubElement(nal_unit, "startCode")
            sc.text = start_code_hex

            SubElement(nal_unit, "forbidden_zero_bit").text = str(fzb)
            SubElement(nal_unit, "nal_unit_type").text = str(nut)
            SubElement(nal_unit, "nuh_layer_id").text = str(nli)
            SubElement(nal_unit, "nuh_temporal_id_plus1").text = str(tid)

            payload = SubElement(nal_unit, "payload")
            payload.text = f"{payload_start} {payload_length}"

            # Parse specific NAL units
            if nut == 32: # VPS
                payload_data = data[payload_start:end_pos]
                vps_info = parse_vps(payload_data)
                if vps_info:
                    vps_elem = SubElement(nal_unit, "VideoParameterSet")

                    # Process parameters using common function
                    internal_vars = process_parameters(vps_elem, vps_info, include_internal_vars)

                    # Add InternalVariables element as last child of VPS if we have internal variables
                    create_internal_variables_element(vps_elem, internal_vars)
            elif nut == 33: # SPS
                payload_data = data[payload_start:end_pos]
                sps_info = parse_sps(payload_data, nli)
                if sps_info:
                    sps_elem = SubElement(nal_unit, "SequenceParameterSet")

                    # Process parameters using common function
                    internal_vars = process_parameters(sps_elem, sps_info, include_internal_vars)

                    # Add InternalVariables element as last child of SPS if we have internal variables
                    create_internal_variables_element(sps_elem, internal_vars)

        # Generate formatted XML
        xml_str = minidom.parseString(tostring(root)).toprettyxml(indent="  ")
        description.write(xml_str)

    def parse_nal_header(self, header_bytes):
        """Parse HEVC NAL unit header from two bytes"""
        if len(header_bytes) < 2:
            raise ValueError("Insufficient header bytes")

        byte1 = header_bytes[0]
        byte2 = header_bytes[1]

        forbidden_zero_bit = (byte1 >> 7) & 0x01
        nal_unit_type = (byte1 >> 1) & 0x3F  # 6 bits
        nuh_layer_id = ((byte1 & 0x01) << 5) | ((byte2 >> 3) & 0x1F)  # 6 bits
        nuh_temporal_id_plus1 = byte2 & 0x07  # 3 bits

        return forbidden_zero_bit, nal_unit_type, nuh_layer_id, nuh_temporal_id_plus1
