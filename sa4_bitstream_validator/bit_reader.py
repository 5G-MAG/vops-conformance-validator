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

    def remaining_bits(self):
        """Get number of remaining bits"""
        return len(self.bitstream) - self.bitstream.pos

    def get_position(self):
        """Get current bit position"""
        return self.bitstream.pos

    def next_bits(self, n):
        """Peek at next n bits without advancing position"""
        if self.bitstream.pos + n > len(self.bitstream):
            return None
        return self.bitstream.peek(f"uint:{n}")

    def is_byte_aligned(self):
        """Check if current position is byte-aligned"""
        return self.bitstream.pos % 8 == 0
