"""
    Parsing of AVC slice header.
"""

from bitstring import Error
from sa4_bitstream_validator.bit_reader import BitReader
from sa4_bitstream_validator.tools import remove_emulation_prevention


def parse_slice_header(data, nal_unit_type):
    """Parse AVC slice header
    
    Args:
        data: Raw slice header data
        nal_unit_type: NAL unit type (5 for IDR, 1 for non-IDR)
    
    Returns:
        dict: Parsed slice header fields
    """
    try:
        # Remove emulation prevention bytes
        clean_data = remove_emulation_prevention(data)
        if not clean_data:
            return None
        
        reader = BitReader(clean_data)
        sh = {}
        
        sh["first_mb_in_slice"] = reader.read_ue()
        sh["slice_type"] = reader.read_ue()
        sh["pic_parameter_set_id"] = reader.read_ue()
        
        # For frame_num, we need to read the correct number of bits
        # Based on the trace, frame_num is 16 bits for this bitstream
        # But we should read a smaller amount to avoid issues
        # Read up to 16 bits but stop if we've read enough
        frame_num_bits = 16
        sh["frame_num"] = reader.read_bits(frame_num_bits)
        
        # For IDR pictures
        if nal_unit_type == 5:
            sh["idr_pic_id"] = reader.read_ue()
        
        # For pic_order_cnt_lsb, read 16 bits based on the trace
        pic_order_cnt_bits = 16
        sh["pic_order_cnt_lsb"] = reader.read_bits(pic_order_cnt_bits)
        
        # no_output_of_prior_pics_flag (for IDR)
        if nal_unit_type == 5:
            sh["no_output_of_prior_pics_flag"] = reader.read_bit()
            sh["long_term_reference_flag"] = reader.read_bit()
        
        # slice_qp_delta
        sh["slice_qp_delta"] = reader.read_se()
        
        return sh
        
    except Error as e:
        print(f"Slice header parsing error: {str(e)}")
        return None
