"""
    Class to read sequence of bits.
"""

from bitstring import ConstBitStream

class BitReader:
    """Helper class to read bits from payload data"""
    def __init__(self, data):
        self.bitstream = ConstBitStream(data)

    def read_bit(self):
        """Read one bit"""
        return self.bitstream.read("uint:1")

    def read_bits(self, n):
        """Read n bits as unsigned integer"""
        return self.bitstream.read(f"uint:{n}")

    def read_uints(self, n, nb):
        """Read an array of n uint"""
        return self.bitstream.readlist([f"uint:{n}"] * nb)

    def read_ue(self):
        """Read unsigned exponential-Golomb code"""
        return self.bitstream.read("ue")

    def read_flags(self, nb):
        """Read a an array of n flags"""
        return self.bitstream.readlist(["uint:1"] * nb)
