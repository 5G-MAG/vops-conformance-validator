"""
Parser for frame_packing_arrangement SEI message (payload type 45)
"""

from sa4_bitstream_validator.bit_reader import BitReader


def parse_frame_packing_arrangement(payload_size, reader):
    """Parse frame_packing_arrangement SEI message (payload type 45)"""
    sei_data = {}

    sei_data["frame_packing_arrangement_id"] = reader.read_ue()
    sei_data["frame_packing_arrangement_cancel_flag"] = reader.read_bit()

    if not sei_data["frame_packing_arrangement_cancel_flag"]:
        sei_data["frame_packing_arrangement_type"] = reader.read_bits(7)
        sei_data["quincunx_sampling_flag"] = reader.read_bit()
        sei_data["content_interpretation_type"] = reader.read_bits(6)
        sei_data["spatial_flipping_flag"] = reader.read_bit()
        sei_data["frame0_flipped_flag"] = reader.read_bit()
        sei_data["field_views_flag"] = reader.read_bit()
        sei_data["current_frame_is_frame0_flag"] = reader.read_bit()
        sei_data["frame0_self_contained_flag"] = reader.read_bit()
        sei_data["frame1_self_contained_flag"] = reader.read_bit()

        if not sei_data["quincunx_sampling_flag"] and sei_data["frame_packing_arrangement_type"] != 5:
            sei_data["frame0_grid_position_x"] = reader.read_bits(4)
            sei_data["frame0_grid_position_y"] = reader.read_bits(4)
            sei_data["frame1_grid_position_x"] = reader.read_bits(4)
            sei_data["frame1_grid_position_y"] = reader.read_bits(4)

        sei_data["frame_packing_arrangement_reserved_byte"] = reader.read_bits(8)
        sei_data["frame_packing_arrangement_persistence_flag"] = reader.read_bit()

    sei_data["upsampled_aspect_ratio_flag"] = reader.read_bit()

    return sei_data
