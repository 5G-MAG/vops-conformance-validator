"""
    Parsing of HEVC short-term reference picture set.
"""

from bitstring import Error

def parse_st_ref_pic_sets(num_short_term_ref_pic_sets: int, is_slice_header: bool, reader):
    """Parse all short-term reference picture set structure"""
    st_ref_pic_sets = {}
    
    # If there are no reference picture sets, return empty dict
    if num_short_term_ref_pic_sets == 0:
        return st_ref_pic_sets
    
    num_negative_pics = [None] * num_short_term_ref_pic_sets
    num_positive_pics = [None] * num_short_term_ref_pic_sets

    num_delta_pocs = [None] * num_short_term_ref_pic_sets
    delta_poc_negative = [None] * num_short_term_ref_pic_sets
    delta_poc_positive = [None] * num_short_term_ref_pic_sets

    #NOTE: Parsing in slice header to be implemented
    max_nb_sets = num_short_term_ref_pic_sets if not is_slice_header else 0

    for k in range(0, max_nb_sets):
        st_ref_pic_set = {}

        try:
            if k != 0:
                st_ref_pic_set[f"inter_ref_pic_set_prediction_flag[k={k}]"] = reader.read_bit()
            else: # Inference
                st_ref_pic_set[f"inter_ref_pic_set_prediction_flag[k={k}]"] = 0

            if st_ref_pic_set[f"inter_ref_pic_set_prediction_flag[k={k}]"]:
                if k == num_short_term_ref_pic_sets:
                    st_ref_pic_set[f"delta_idx_minus1[k={k}]"] = reader.read_ue()
                else: # Inference
                    st_ref_pic_set[f"delta_idx_minus1[k={k}]"] = 0

                st_ref_pic_set[f"delta_rps_sign[k={k}]"] = reader.read_bit()
                st_ref_pic_set[f"abs_delta_rps_minus1[k={k}]"] = reader.read_ue()

                ref_rps_idx = k - ( st_ref_pic_set[f"delta_idx_minus1[k={k}]"] + 1 )
                assert 0 <= ref_rps_idx < k

                for j in range(0, num_delta_pocs[ref_rps_idx]+1):
                    st_ref_pic_set[f"used_by_curr_pic_flag[k={k}][j={j}]"] = reader.read_bit()
                    if not st_ref_pic_set[f"used_by_curr_pic_flag[k={k}][j={j}]"]:
                        st_ref_pic_set[f"use_delta_flag[k={k}][j={j}]"] = reader.read_bit()

                # Variable derivation
                delta_rps = ((1 - 2 * st_ref_pic_set[f"delta_rps_sign[k={k}]"])
                            * (st_ref_pic_set[f"abs_delta_rps_minus1[k={k}]"] + 1))

                # Get reference delta_pocs from stored values
                ref_negative = delta_poc_negative[ref_rps_idx]
                ref_positive = delta_poc_positive[ref_rps_idx]
                ref_delta_poc = ref_negative + ref_positive

                # Calculate valid_dps including new delta_rps entry
                valid_dps = []
                for j in range(num_delta_pocs[ref_rps_idx] + 1):
                    if j < len(ref_delta_poc):
                        dp = ref_delta_poc[j] + delta_rps
                    else:
                        dp = delta_rps  # Additional entry

                    if (st_ref_pic_set[f"used_by_curr_pic_flag[k={k}][j={j}]"] or
                        (not st_ref_pic_set[f"used_by_curr_pic_flag[k={k}][j={j}]"] and
                         st_ref_pic_set[f"use_delta_flag[k={k}][j={j}]"])):
                        valid_dps.append(dp)

                # Store derived delta_pocs for future reference
                negative_dps = sorted([dp for dp in valid_dps if dp < 0], reverse=True)
                positive_dps = sorted([dp for dp in valid_dps if dp > 0])
                delta_poc_negative[k] = negative_dps
                delta_poc_positive[k] = positive_dps

                # Final counts
                num_negative_pics[k] = len(negative_dps)
                num_positive_pics[k] = len(positive_dps)
                num_delta_pocs[k] = num_negative_pics[k] + num_positive_pics[k]
            else:
                # Inference
                st_ref_pic_set[f"delta_idx_minus1[k={k}]"] = 0

                st_ref_pic_set[f"num_negative_pics[k={k}]"] = reader.read_ue()
                st_ref_pic_set[f"num_positive_pics[k={k}]"] = reader.read_ue()
                for i in range(0, st_ref_pic_set[f"num_negative_pics[k={k}]"]):
                    st_ref_pic_set[f"delta_poc_s0_minus1[k={k}][i={i}]"] = reader.read_ue()
                    st_ref_pic_set[f"used_by_curr_pic_s0_flag[k={k}][i={i}]"] = reader.read_bit()

                for i in range(0, st_ref_pic_set[f"num_positive_pics[k={k}]"]):
                    st_ref_pic_set[f"delta_poc_s1_minus1[k={k}][i={i}]"] = reader.read_ue()
                    st_ref_pic_set[f"used_by_curr_pic_s1_flag[k={k}][i={i}]"] = reader.read_bit()

                # Variable derivation
                num_negative_pics[k] = st_ref_pic_set[f"num_negative_pics[k={k}]"]
                num_positive_pics[k] = st_ref_pic_set[f"num_positive_pics[k={k}]"]
                num_delta_pocs[k] = num_negative_pics[k] + num_positive_pics[k]

                delta_poc_s0 = []
                current_poc = 0
                for i in range(num_negative_pics[k]):
                    delta_poc = current_poc - (st_ref_pic_set[f"delta_poc_s0_minus1[k={k}][i={i}]"] + 1)
                    delta_poc_s0.append(delta_poc)
                    current_poc = delta_poc
                delta_poc_negative[k] = delta_poc_s0

                delta_poc_s1 = []
                current_poc = 0
                for i in range(num_positive_pics[k]):
                    delta_poc = current_poc + (st_ref_pic_set[f"delta_poc_s1_minus1[k={k}][i={i}]"] + 1)
                    delta_poc_s1.append(delta_poc)
                    current_poc = delta_poc
                delta_poc_positive[k] = delta_poc_s1

        except Error as e:
            print(f"Short-term reference picture set parsing error: {e}")
            # Return empty dict instead of None to avoid breaking the SPS parser
            return {}

        st_ref_pic_sets = {
            **st_ref_pic_sets,
            **st_ref_pic_set,
        }
    return st_ref_pic_sets
