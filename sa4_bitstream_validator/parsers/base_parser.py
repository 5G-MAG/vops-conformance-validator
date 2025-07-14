"""
    Base parser of media bitstreams.
"""

import abc

class BaseParser(abc.ABC):
    """Base class of all the parsers."""
    @abc.abstractmethod
    def bitstream_to_xml(self, bitstream, description):
        "Parse a bitstream and generate its XML description."
