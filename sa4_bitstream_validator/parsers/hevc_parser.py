"""
    Parsers of HEVC bitstreams.
"""

import re
from xml.etree.ElementTree import SubElement

from sa4_bitstream_validator.parsers.base_parser import (
    BaseParser,
    extract_parameter_value,
    create_indexed_element,
    create_regular_element,
    create_internal_variables_element
)
from sa4_bitstream_validator.parsers.hevc import parse_sps
from sa4_bitstream_validator.parsers.hevc import parse_vps
from sa4_bitstream_validator.parsers.hevc.sei import parse_sei_rbsp


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


class HEVCParser(BaseParser):
    """Parser of HEVC bitstreams."""
    
    def get_codec_name(self):
        """Return codec name for XML root element."""
        return "HEVC"
    
    def nal_header_size(self):
        """Return NAL header size in bytes (2 for HEVC)."""
        return 2
    
    def parse_nal_header(self, header_bytes):
        """Parse HEVC NAL unit header from two bytes"""
        if len(header_bytes) < 2:
            raise ValueError("Insufficient header bytes")

        byte1 = header_bytes[0]
        byte2 = header_bytes[1]

        return {
            'forbidden_zero_bit': (byte1 >> 7) & 0x01,
            'nal_unit_type': (byte1 >> 1) & 0x3F,
            'nuh_layer_id': ((byte1 & 0x01) << 5) | ((byte2 >> 3) & 0x1F),
            'nuh_temporal_id_plus1': byte2 & 0x07
        }
    
    def write_nal_header_to_xml(self, nal_unit, parsed_header):
        """Write HEVC NAL header fields as XML elements."""
        SubElement(nal_unit, "forbidden_zero_bit").text = str(parsed_header['forbidden_zero_bit'])
        SubElement(nal_unit, "nal_unit_type").text = str(parsed_header['nal_unit_type'])
        SubElement(nal_unit, "nuh_layer_id").text = str(parsed_header['nuh_layer_id'])
        SubElement(nal_unit, "nuh_temporal_id_plus1").text = str(parsed_header['nuh_temporal_id_plus1'])
    
    def parse_nal_payload(self, parsed_header, data, payload_start, end_pos, 
                          nal_unit, include_internal_vars):
        """Dispatch to HEVC-specific parsers."""
        nut = parsed_header['nal_unit_type']
        nli = parsed_header['nuh_layer_id']
        
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

        # Parse SEI NAL units (PREFIX_SEI_NUT = 39, SUFFIX_SEI_NUT = 40)
        elif nut == 39 or nut == 40: # SEI
            payload_data = data[payload_start:end_pos]
            sei_messages = parse_sei_rbsp(payload_data)
            if sei_messages:
                sei_elem = SubElement(nal_unit, "SEI")
                sei_elem.set("nal_unit_type", "prefix" if nut == 39 else "suffix")

                for i, sei_message in enumerate(sei_messages):
                    message_elem = SubElement(sei_elem, "SEIMessage")
                    message_elem.set("index", str(i))

                    # Add payload type and size
                    SubElement(message_elem, "payload_type").text = str(sei_message.get("payload_type", ""))
                    SubElement(message_elem, "payload_size").text = str(sei_message.get("payload_size", ""))

                    # Add payload data
                    payload = sei_message.get("payload", {})
                    if payload:
                        payload_elem = SubElement(message_elem, "payload")

                        if sei_message.get("payload_type") == 45:
                            fp_elem = SubElement(payload_elem, "frame_packing_arrangement")

                            # Process parameters using common function (payload is already flattened by SEI parser)
                            internal_vars = process_parameters(fp_elem, payload, include_internal_vars)

                            # Add InternalVariables element if we have internal variables
                            create_internal_variables_element(fp_elem, internal_vars)
                        elif sei_message.get("payload_type") == 176:
                            three_d_elem = SubElement(payload_elem, "three_dimensional_reference_displays_info")

                            # Process parameters using common function (payload is already flattened by SEI parser)
                            internal_vars = process_parameters(three_d_elem, payload, include_internal_vars)

                            # Add InternalVariables element if we have internal variables
                            create_internal_variables_element(three_d_elem, internal_vars)
                        else:
                            # For unsupported SEI types, just add the type
                            type_elem = SubElement(payload_elem, "type")
                            type_elem.text = payload.get("type", "unknown")
