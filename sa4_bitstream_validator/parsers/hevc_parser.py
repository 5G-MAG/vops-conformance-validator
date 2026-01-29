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

                    # Collect internal variables separately to add them at the end
                    internal_vars = []

                    for key, value in vps_info.items():
                        # Skip internal variables if not requested
                        if not include_internal_vars and key.startswith("_"):
                            continue

                        # Remove underscore prefix from internal variables when including them
                        xml_key = key[1:] if key.startswith("_") and include_internal_vars else key

                        # Handle internal variables by collecting them for later
                        if key.startswith("_") and include_internal_vars:
                            internal_vars.append((xml_key, value))
                        else:
                            # Regular (non-internal) parameters go directly in VPS element
                            # Handle indexed parameters by extracting variable names and values from encoded keys
                            # New format: field[k={k}][j={j}] -> extract variable names 'k', 'j' and their values
                            match_new_format = re.match(r"^([^\[]+?)((?:\[[^=]+=\d+\])+)$", xml_key)
                            if match_new_format:
                                base_key = match_new_format.group(1)
                                index_parts = match_new_format.group(2)

                                # Extract all variable=value pairs
                                var_value_pairs = re.findall(r"\[([^=]+)=(\d+)\]", index_parts)

                                elem = SubElement(vps_elem, base_key)
                                for var_name, var_value in var_value_pairs:
                                    elem.set(var_name, var_value)
                                elem.text = str(value)
                            else:
                                # Regular parameter without index
                                elem = SubElement(vps_elem, xml_key)
                                elem.text = str(value)

                    # Add InternalVariables element as last child of VPS if we have internal variables
                    if internal_vars:
                        internal_vars_elem = SubElement(vps_elem, "InternalVariables")
                        for xml_key, value in internal_vars:
                            # Handle indexed parameters by extracting variable names and values from encoded keys
                            # New format: field[k={k}][j={j}] -> extract variable names 'k', 'j' and their values
                            match_new_format = re.match(r"^([^\[]+?)((?:\[[^=]+=\d+\])+)$", xml_key)
                            if match_new_format:
                                base_key = match_new_format.group(1)
                                index_parts = match_new_format.group(2)

                                # Extract all variable=value pairs
                                var_value_pairs = re.findall(r"\[([^=]+)=(\d+)\]", index_parts)

                                elem = SubElement(internal_vars_elem, base_key)
                                for var_name, var_value in var_value_pairs:
                                    elem.set(var_name, var_value)
                                elem.text = str(value)
                            else:
                                # Regular parameter without index
                                elem = SubElement(internal_vars_elem, xml_key)
                                elem.text = str(value)
            elif nut == 33: # SPS
                payload_data = data[payload_start:end_pos]
                sps_info = parse_sps(payload_data, nli)
                if sps_info:
                    sps_elem = SubElement(nal_unit, "SequenceParameterSet")
                    for key, value in sps_info.items():
                        # Skip internal variables if not requested
                        if not include_internal_vars and key.startswith("_"):
                            continue

                        # Remove underscore prefix from internal variables when including them
                        xml_key = key[1:] if key.startswith("_") and include_internal_vars else key

                        # Handle indexed parameters by extracting variable names and values from encoded keys
                        # Format: field[k={k}][j={j}] -> extract variable names 'k', 'j' and their values

                        # Pattern to match: field[name1=value1][name2=value2]...
                        match_new_format = re.match(r"^([^\[]+?)((?:\[[^=]+=\d+\])+)$", xml_key)
                        if match_new_format:
                            base_key = match_new_format.group(1)
                            index_parts = match_new_format.group(2)

                            # Extract all variable=value pairs
                            var_value_pairs = re.findall(r"\[([^=]+)=(\d+)\]", index_parts)

                            elem = SubElement(sps_elem, base_key)
                            for var_name, var_value in var_value_pairs:
                                elem.set(var_name, var_value)
                            elem.text = str(value)
                        else:
                            # Regular parameter without index
                            elem = SubElement(sps_elem, xml_key)
                            elem.text = str(value)

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
