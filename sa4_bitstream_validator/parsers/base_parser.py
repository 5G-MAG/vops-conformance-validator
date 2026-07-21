"""
    Base parser of media bitstreams.
"""

import abc
import re
import binascii
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from sa4_bitstream_validator.tools import find_start_codes


def extract_parameter_value(value):
    """Extract actual value and inferred flag from ParsedValue object or regular value"""
    is_inferred = False
    actual_value = value
    if hasattr(value, 'inferred') and hasattr(value, 'value'):
        is_inferred = value.inferred
        actual_value = value
    return actual_value, is_inferred


def create_indexed_element(parent_elem, xml_key, actual_value, is_inferred=False):
    """Create XML element for indexed parameters like field[i={i}]"""
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

        elem.text = str(actual_value)
        return elem
    return None


def create_regular_element(parent_elem, xml_key, actual_value, is_inferred=False):
    """Create XML element for regular (non-indexed) parameters"""
    elem = SubElement(parent_elem, xml_key)
    if is_inferred:
        elem.set("inferred", "true")

    elem.text = str(actual_value)
    return elem


def create_internal_variables_element(parent_elem, internal_vars):
    """Create InternalVariables element with collected internal variables"""
    if internal_vars:
        internal_vars_elem = SubElement(parent_elem, "InternalVariables")
        for xml_key, value in internal_vars:
            actual_value, _ = extract_parameter_value(value)

            indexed_elem = create_indexed_element(internal_vars_elem, xml_key, actual_value)
            if indexed_elem is None:
                create_regular_element(internal_vars_elem, xml_key, actual_value)


class BaseParser(abc.ABC):
    """Base class of all the parsers."""
    
    @abc.abstractmethod
    def get_codec_name(self) -> str:
        """Return codec name for XML root element (e.g., 'AVC', 'HEVC')."""
    
    @abc.abstractmethod
    def nal_header_size(self) -> int:
        """Return NAL header size in bytes (1 for AVC, 2 for HEVC)."""
    
    @abc.abstractmethod
    def parse_nal_header(self, header_bytes):
        """Parse NAL header; return dict of header fields."""
    
    @abc.abstractmethod
    def write_nal_header_to_xml(self, nal_unit, parsed_header):
        """Write NAL header fields as XML elements."""
    
    @abc.abstractmethod
    def parse_nal_payload(self, parsed_header, data, payload_start, end_pos, 
                          nal_unit, include_internal_vars):
        """Dispatch to codec-specific parsers; populate nal_unit with parsed elements."""
    
    def bitstream_to_xml(self, bitstream, description, include_internal_vars=False):
        """Shared bitstream-to-XML pipeline."""
        data = bitstream.read()
        start_codes = find_start_codes(data)
        if not start_codes:
            print("Error: No NAL units found in bitstream")
            return

        root = Element(f"{self.get_codec_name()}Bitstream")
        root.set("uri", bitstream.name)

        for i in range(len(start_codes)):
            start_pos, start_len = start_codes[i]
            
            # Shared boundary calculation
            if i < len(start_codes) - 1:
                next_start, _ = start_codes[i+1]
                end_pos = next_start
            else:
                end_pos = len(data)

            # Shared start code extraction
            start_code_hex = binascii.hexlify(data[start_pos:start_pos+start_len]).decode().upper()

            # Shared header parsing
            header_start = start_pos + start_len
            if header_start + self.nal_header_size() > end_pos:
                continue

            header_bytes = data[header_start:header_start+self.nal_header_size()]
            try:
                parsed_header = self.parse_nal_header(header_bytes)
            except ValueError:
                continue

            # Shared payload calculation
            payload_start = header_start + self.nal_header_size()
            payload_length = end_pos - payload_start

            # Shared XML element creation
            nal_unit = SubElement(root, "NALUnit")
            sc = SubElement(nal_unit, "startCode")
            sc.text = start_code_hex
            
            # Codec-specific header fields
            self.write_nal_header_to_xml(nal_unit, parsed_header)

            payload = SubElement(nal_unit, "payload")
            payload.text = f"{payload_start} {payload_length}"

            # Codec-specific payload parsing
            self.parse_nal_payload(parsed_header, data, payload_start, end_pos, 
                                   nal_unit, include_internal_vars)

        # Shared XML serialization
        xml_str = minidom.parseString(tostring(root)).toprettyxml(indent="  ")
        description.write(xml_str)
