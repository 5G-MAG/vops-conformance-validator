"""
    Parsers of AVC bitstreams.
"""

from xml.etree.ElementTree import SubElement

from sa4_bitstream_validator.parsers.base_parser import (
    BaseParser,
    extract_parameter_value,
    create_indexed_element,
    create_regular_element,
    create_internal_variables_element
)
from sa4_bitstream_validator.parsers.avc.sps import parse_sps
from sa4_bitstream_validator.parsers.avc.pps import parse_pps
from sa4_bitstream_validator.parsers.avc.slice_header import parse_slice_header


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
        elif isinstance(value, dict):
            # Handle nested dictionaries (e.g., VUIParameters)
            nested_elem = SubElement(parent_elem, xml_key)
            nested_internal_vars = process_parameters(nested_elem, value, include_internal_vars)
            # Add internal variables from nested dict
            if nested_internal_vars:
                create_internal_variables_element(nested_elem, nested_internal_vars)
        else:
            actual_value, _ = extract_parameter_value(value)

            # Try indexed parameter first, then fall back to regular
            indexed_elem = create_indexed_element(parent_elem, xml_key, actual_value)
            if indexed_elem is None:
                create_regular_element(parent_elem, xml_key, actual_value)

    return internal_vars


class AVCParser(BaseParser):
    """Parser of AVC bitstreams."""
    
    def get_codec_name(self):
        """Return codec name for XML root element."""
        return "AVC"
    
    def nal_header_size(self):
        """Return NAL header size in bytes (1 for AVC)."""
        return 1
    
    def parse_nal_header(self, header_bytes):
        """Parse AVC NAL unit header from one byte"""
        header_byte = header_bytes[0]
        return {
            'forbidden_zero_bit': (header_byte >> 7) & 0x01,
            'nal_ref_idc': (header_byte >> 5) & 0x03,
            'nal_unit_type': header_byte & 0x1F
        }
    
    def write_nal_header_to_xml(self, nal_unit, parsed_header):
        """Write AVC NAL header fields as XML elements."""
        SubElement(nal_unit, "forbidden_zero_bit").text = str(parsed_header['forbidden_zero_bit'])
        SubElement(nal_unit, "nal_ref_idc").text = str(parsed_header['nal_ref_idc'])
        SubElement(nal_unit, "nal_unit_type").text = str(parsed_header['nal_unit_type'])
    
    def parse_nal_payload(self, parsed_header, data, payload_start, end_pos, 
                          nal_unit, include_internal_vars):
        """Dispatch to AVC-specific parsers."""
        nal_unit_type = parsed_header['nal_unit_type']
        
        # Parse specific NAL units
        if nal_unit_type == 7:  # SPS
            payload_data = data[payload_start:end_pos]
            sps_info = parse_sps(payload_data)
            if sps_info:
                sps_elem = SubElement(nal_unit, "SequenceParameterSet")
                self.last_sps_elem = sps_elem  # Track for InternalVariables

                # Process parameters using common function
                internal_vars = process_parameters(sps_elem, sps_info, include_internal_vars)

                # Add InternalVariables element as last child of SPS if we have internal variables
                create_internal_variables_element(sps_elem, internal_vars)
        
        elif nal_unit_type == 8:  # PPS
            payload_data = data[payload_start:end_pos]
            pps_info = parse_pps(payload_data)
            if pps_info:
                pps_elem = SubElement(nal_unit, "PictureParameterSet")

                # Process parameters using common function
                internal_vars = process_parameters(pps_elem, pps_info, include_internal_vars)

                # Add InternalVariables element as last child of PPS if we have internal variables
                create_internal_variables_element(pps_elem, internal_vars)
        
        elif nal_unit_type in [1, 5]:  # Coded slice (IDR or non-IDR)
            payload_data = data[payload_start:end_pos]
            slice_info = parse_slice_header(payload_data, nal_unit_type)
            if slice_info:
                slice_elem = SubElement(nal_unit, "SliceHeader")

                # Process parameters using common function
                internal_vars = process_parameters(slice_elem, slice_info, include_internal_vars)

                # Add InternalVariables element as last child of SliceHeader if we have internal variables
                create_internal_variables_element(slice_elem, internal_vars)
                
                # Count slices per picture (group by frame_num)
                frame_num = slice_info.get("frame_num", 0)
                if frame_num not in self.picture_slice_counts:
                    self.picture_slice_counts[frame_num] = 0
                self.picture_slice_counts[frame_num] += 1
    
    def bitstream_to_xml(self, bitstream, description, include_internal_vars=False):
        """Parse an AVC bitstream with slice counting."""
        # Track slice counts per picture (grouped by frame_num)
        self.picture_slice_counts = {}  # frame_num -> slice_count
        self.last_sps_elem = None  # Track last SPS element for InternalVariables
        
        # Call parent template method
        super().bitstream_to_xml(bitstream, description, include_internal_vars)
        
        # Add parser variables as InternalVariables inside the last SPS
        if include_internal_vars and self.last_sps_elem is not None:
            # Calculate slice count statistics
            if self.picture_slice_counts:
                max_slices = max(self.picture_slice_counts.values())
                total_pictures = len(self.picture_slice_counts)
                
                # Use _CamelCase naming convention (matching HEVC parser)
                parser_vars = {
                    "_MaxPictureSliceCount": max_slices,
                    "_PictureCount": total_pictures
                }
                
                # Add per-picture slice counts (using i={frame_num} for indexed element)
                for frame_num, count in self.picture_slice_counts.items():
                    parser_vars[f"_PictureSliceCount[i={frame_num}]"] = count
                
                # Find or create InternalVariables element inside SPS
                internal_vars_elem = self.last_sps_elem.find("InternalVariables")
                if internal_vars_elem is None:
                    internal_vars_elem = SubElement(self.last_sps_elem, "InternalVariables")
                
                # Process each parser variable - remove _ prefix and create elements
                for key, value in parser_vars.items():
                    actual_value, _ = extract_parameter_value(value)
                    
                    # Remove _ prefix for XML element name
                    xml_key = key[1:] if key.startswith("_") else key
                    
                    # Try indexed parameter first, then fall back to regular
                    indexed_elem = create_indexed_element(internal_vars_elem, xml_key, actual_value)
                    if indexed_elem is None:
                        create_regular_element(internal_vars_elem, xml_key, actual_value)
