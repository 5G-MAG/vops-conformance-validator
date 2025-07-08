"""
    Class to read sequence of bits.
"""

class BitReader:
    """Helper class to read bits from payload data"""
    def __init__(self, data):
        self.data = data
        self.byte_pos = 0
        self.bit_pos = 0  # 0-7, MSB first

    def read_bit(self):
        """Read one bit"""
        if self.byte_pos >= len(self.data):
            return None
        bit = (self.data[self.byte_pos] >> (7 - self.bit_pos)) & 1
        self.bit_pos += 1
        if self.bit_pos >= 8:
            self.byte_pos += 1
            self.bit_pos = 0
        return bit

    def read_bits(self, n):
        """Read n bits as unsigned integer"""
        value = 0
        for _ in range(n):
            bit = self.read_bit()
            if bit is None:
                break
            value = (value << 1) | bit
        return value

    def read_ue(self):
        """Read unsigned exponential-Golomb code"""
        leading_zeros = 0
        while self.read_bit() == 0:
            leading_zeros += 1
            if leading_zeros > 32:
                raise ValueError("Invalid UE code")
        value = (1 << leading_zeros) - 1
        for i in range(leading_zeros):
            bit = self.read_bit()
            if bit is None:
                break
            value += bit << (leading_zeros - 1 - i)
        return value
