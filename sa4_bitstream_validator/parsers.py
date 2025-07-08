"""
    HEVC parsing functions.
"""

import binascii
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

import abc

from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import find_start_codes
from sa4_bitstream_validator.tools import remove_emulation_prevention

class BaseParser(abc.ABC):
    @abc.abstractmethod
    def bitstream_to_xml(self, bitstream, description):
        "Parse a bitstream and generate its XML description."

class HEVCParser(BaseParser):
    """Parser of HEVC bitstreams and HEVC XML description."""
    def bitstream_to_xml(self, bitstream, description):
        "Parse a HEVC bitstream"
        data = bitstream.read()
        start_codes = find_start_codes(data)
        if not start_codes:
            print("Error: No NAL units found in bitstream")
            return

        # Create XML root element with namespaces
        root = Element('HEVCBitstream')
        root.set('xmlns', 'urn:mpeg:mpeg21:example:HEVC')
        root.set('xmlns:bs1', 'urn:mpeg:mpeg21:2003:01-DIA-BSDL1-NS')
        root.set('bs1:bitstreamURI', bitstream.name)

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
            nal_unit = SubElement(root, 'NALUnit')

            sc = SubElement(nal_unit, 'startCode')
            sc.text = start_code_hex

            SubElement(nal_unit, 'forbidden_zero_bit').text = str(fzb)
            SubElement(nal_unit, 'nal_unit_type').text = str(nut)
            SubElement(nal_unit, 'nuh_layer_id').text = str(nli)
            SubElement(nal_unit, 'nuh_temporal_id_plus1').text = str(tid)

            payload = SubElement(nal_unit, 'payload')
            payload.text = f"{payload_start} {payload_length}"

            # Add VPS parsing for NAL type 32
            if nut == 32:
                payload_data = data[payload_start:end_pos]
                vps_info = self.parse_vps(payload_data)
                if vps_info:
                    vps_elem = SubElement(nal_unit, 'VideoParameterSet')
                    for key, value in vps_info.items():
                        elem = SubElement(vps_elem, key)
                        elem.text = str(value)

        # Generate formatted XML
        xml_str = minidom.parseString(tostring(root)).toprettyxml(indent="  ")
        description.write(xml_str)

    def parse_vps(self, payload_data):
        """Parse Video Parameter Set from payload bytes"""
        try:
            # Remove emulation prevention bytes
            clean_data = remove_emulation_prevention(payload_data)
            if not clean_data:
                return None

            reader = BitReader(clean_data)

            # Parse basic VPS parameters
            vps = {
                'vps_video_parameter_set_id': reader.read_ue(),
                'vps_base_layer_internal_flag': reader.read_bit(),
                'vps_base_layer_available_flag': reader.read_bit(),
                'vps_max_layers_minus1': reader.read_bits(6),
                'vps_max_sub_layers_minus1': reader.read_bits(3),
                'vps_temporal_id_nesting_flag': reader.read_bit(),
                'vps_reserved_0xffff_16bits': reader.read_bits(16)
            }

            return {k: v for k, v in vps.items() if v is not None}

        except Exception as e:
            print(f"VPS parsing error: {str(e)}")
            return None


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
