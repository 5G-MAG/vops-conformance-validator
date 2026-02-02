"""
Parser for three_dimensional_reference_displays_info SEI message (payload type 176)
"""

from sa4_bitstream_validator.bit_reader import BitReader


def _calculate_mantissa_bits(exponent, precision):
    """Calculate the number of bits needed for mantissa according to HEVC spec"""
    if exponent == 0:
        return max(0, precision - 30)
    else:
        return max(0, exponent + precision - 31)


def parse_three_dimensional_reference_displays_info(payload_size, reader):
    """Parse three_dimensional_reference_displays_info SEI message"""
    sei_data = {}

    sei_data["prec_ref_display_width"] = reader.read_ue()
    sei_data["ref_viewing_distance_flag"] = reader.read_bit()

    if sei_data["ref_viewing_distance_flag"]:
        sei_data["prec_ref_viewing_dist"] = reader.read_ue()

    sei_data["num_ref_displays_minus1"] = reader.read_ue()

    for i in range(sei_data["num_ref_displays_minus1"] + 1):
        sei_data[f"left_view_id[i={i}]"] = reader.read_ue()
        sei_data[f"right_view_id[i={i}]"] = reader.read_ue()
        sei_data[f"exponent_ref_display_width[i={i}]"] = reader.read_bits(6)

        # Calculate number of bits for mantissa_ref_display_width using common function
        ref_disp_width_bits = _calculate_mantissa_bits(
            sei_data[f"exponent_ref_display_width[i={i}]"],
            sei_data["prec_ref_display_width"]
        )
        sei_data[f"mantissa_ref_display_width[i={i}]"] = reader.read_bits(ref_disp_width_bits)

        if sei_data["ref_viewing_distance_flag"]:
            sei_data[f"exponent_ref_viewing_distance[i={i}]"] = reader.read_bits(6)

            # Calculate number of bits for mantissa_ref_viewing_distance using common function
            ref_view_dist_bits = _calculate_mantissa_bits(
                sei_data[f"exponent_ref_viewing_distance[i={i}]"],
                sei_data["prec_ref_viewing_dist"]
            )
            sei_data[f"mantissa_ref_viewing_distance[i={i}]"] = reader.read_bits(ref_view_dist_bits)

        sei_data[f"additional_shift_present_flag[i={i}]"] = reader.read_bit()
        if sei_data[f"additional_shift_present_flag[i={i}]"]:
            sei_data[f"num_sample_shift_plus512[i={i}]"] = reader.read_bits(10)

    sei_data["three_dimensional_reference_displays_extension_flag"] = reader.read_bit()

    return sei_data