"""
    AVC bitstream parsing module.
"""

from .sps import parse_sps
from .pps import parse_pps
from .vui import parse_vui_parameters
from .slice_header import parse_slice_header

__all__ = ['parse_sps', 'parse_pps', 'parse_vui_parameters', 'parse_slice_header']
