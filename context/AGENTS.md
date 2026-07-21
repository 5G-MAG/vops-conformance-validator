# AGENTS.md - Bitstream Validator Project Guide

## Project Overview

This project validates video bitstreams against 3GPP TS 26.265 operation points using XSD schema validation.

## Architecture

```
bitstream-validator/
├── config.yaml                    # Operation point definitions
├── bitstream_rules/               # XSD schemas for validation
│   ├── hevc_common.xsd           # HEVC type definitions
│   ├── avc_common.xsd            # AVC type definitions
│   ├── 3gpp-hevc-main10-main-41.xsd  # HEVC HD
│   ├── 3gpp-hevc-uhd-op.xsd      # HEVC UHD
│   ├── 3gpp-hevc-hdr-colour.xsd  # HDR colour assertions (reusable)
│   ├── 3gpp-avc-hd-op.xsd        # AVC HD profile/level
│   ├── 3gpp-avc_rate_constraints.xsd  # AVC rate constraints
│   └── ...
├── sa4_bitstream_validator/
│   ├── __main__.py               # CLI (dump, check, validate)
│   ├── validators.py             # XMLValidator class
│   ├── parsers/
│   │   ├── base_parser.py        # Abstract parser interface + shared XML helpers
│   │   ├── hevc_parser.py        # HEVC bitstream → XML
│   │   ├── avc_parser.py         # AVC bitstream → XML
│   │   ├── hevc/                 # HEVC parsing modules
│   │   └── avc/                  # AVC parsing modules
│   └── tools.py                  # Utility functions
└── context/
    ├── 26265-j20.md              # 3GPP TS 26.265 spec
    └── AGENTS.md                 # This file
```

## Parser Architecture

### Template Method Pattern

The parsers use a template method pattern to eliminate code duplication:

```
BaseParser (base_parser.py)
├── extract_parameter_value()      # Unified value extraction with is_inferred support
├── create_indexed_element()       # XML element for indexed parameters
├── create_regular_element()       # XML element for regular parameters
├── create_internal_variables_element()  # InternalVariables container
├── bitstream_to_xml()             # Template method (shared scaffolding)
│   ├── get_codec_name()           # Abstract: "AVC" or "HEVC"
│   ├── nal_header_size()          # Abstract: 1 for AVC, 2 for HEVC
│   ├── parse_nal_header()         # Abstract: parse header bytes
│   ├── write_nal_header_to_xml()  # Abstract: write header to XML
│   └── parse_nal_payload()        # Abstract: dispatch to codec parsers
├── AVCParser (avc_parser.py)
│   ├── process_parameters()       # Handles nested dicts (VUIParameters)
│   └── bitstream_to_xml()         # Overrides to add slice counting
└── HEVCParser (hevc_parser.py)
    ├── process_parameters()       # Handles profile_tier_level, rep_format
    ├── create_profile_tier_level_element()  # HEVC-specific nested structure
    └── create_rep_format_element()          # HEVC-specific nested structure
```

### Shared Functions in `base_parser.py`

| Function | Purpose |
|----------|---------|
| `extract_parameter_value(value)` | Returns `(actual_value, is_inferred)` tuple. Fixes AVC bug where value was returned unchanged. |
| `create_indexed_element(parent, key, value, is_inferred)` | Creates XML element for indexed parameters like `field[i=3]` |
| `create_regular_element(parent, key, value, is_inferred)` | Creates XML element for regular parameters |
| `create_internal_variables_element(parent, internal_vars)` | Creates `<InternalVariables>` container |

### Template Method `bitstream_to_xml()`

The template method in `BaseParser` handles the shared pipeline:

1. Read bitstream data
2. Find start codes
3. Create XML root element (`{codec}Bitstream`)
4. For each NAL unit:
   - Calculate boundaries
   - Extract start code hex
   - Parse NAL header (codec-specific)
   - Write header to XML (codec-specific)
   - Parse payload (codec-specific)
5. Serialize XML to pretty-printed string

Codec-specific behavior is implemented via abstract methods:
- `get_codec_name()`: Returns "AVC" or "HEVC"
- `nal_header_size()`: Returns 1 for AVC, 2 for HEVC
- `parse_nal_header(header_bytes)`: Returns dict of header fields
- `write_nal_header_to_xml(nal_unit, parsed_header)`: Writes header fields as XML
- `parse_nal_payload(...)`: Dispatches to codec-specific parsers

## Workflow

### 1. Bitstream → XML → Validation

```bash
# Dump HEVC bitstream to XML
python -m sa4_bitstream_validator dump bitstream.hevc output.xml

# Dump AVC bitstream to XML
python -m sa4_bitstream_validator dump bitstream.264 output.xml --codec avc

# Validate against XSD schemas
python -m sa4_bitstream_validator check output.xml bitstream_rules/schema.xsd

# Validate against operation point (config.yaml)
python -m sa4_bitstream_validator validate bitstream.hevc 3GPP-HEVC-HD --report report.json

# Validate AVC bitstream against operation point
python -m sa4_bitstream_validator validate bitstream.264 3GPP-AVC-HD --codec avc --report report.json
```

### 2. Operation Points (config.yaml)

Each operation point defines:
- Description
- XSD schemas to validate against (AND logic)
- OR conditions (list of schemas where one must pass)

Example:
```yaml
operation_points:
  3GPP-HEVC-HD:
    description: "HEVC HD Operation Point"
    xsds:
      - bitstream_rules/3gpp-hevc-main10-main-41.xsd
```

## XSD Schema Patterns

### Structure
```xml
<xs:schema vc:minVersion="1.1">
  <xs:include schemaLocation="hevc_common.xsd"/>
  
  <xs:element name="HEVCBitstream">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="NALUnit" maxOccurs="unbounded"/>
      </xs:sequence>
      
      <!-- Assertions -->
      <xs:assert test="NALUnit[nuh_layer_id=0]/SequenceParameterSet/general_profile_idc = 2"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

### Common Assertion Patterns (HEVC)

| Constraint | XPath Expression |
|------------|------------------|
| Profile | `NALUnit[nuh_layer_id=0]/SequenceParameterSet/general_profile_idc = 2` |
| Level | `NALUnit[nuh_layer_id=0]/SequenceParameterSet/general_level_idc = 123` |
| Tier | `string(NALUnit[nuh_layer_id=0]/SequenceParameterSet/general_tier_flag) = '0'` |
| Progressive | `string(NALUnit[nuh_layer_id=0]/SequenceParameterSet/general_progressive_source_flag) = '1'` |
| HDR Colour | `NALUnit[nuh_layer_id=0]/SequenceParameterSet/colour_primaries = 9` |

### Common Assertion Patterns (AVC)

| Constraint | XPath Expression |
|------------|------------------|
| Profile | `NALUnit/SequenceParameterSet/profile_idc = 100` |
| Level | `NALUnit/SequenceParameterSet/level_idc = 40` |
| Progressive High | `NALUnit/SequenceParameterSet/constraint_set4_flag = 1` |
| MV Length (H) | `NALUnit/SequenceParameterSet/VUIParameters/log2_max_mv_length_horizontal <= 11` |
| MV Length (V) | `NALUnit/SequenceParameterSet/VUIParameters/log2_max_mv_length_vertical <= 9` |
| Max Slices | `NALUnit/SequenceParameterSet/InternalVariables/MaxPictureSliceCount <= 16` |

## 3GPP Spec Reference

### Implemented Operation Points (TS 26.265)

| Operation Point | Codec | Profile | Level | Format | Status |
|-----------------|-------|---------|-------|--------|--------|
| 3GPP-HEVC-HD | HEVC | Main 10 | 4.1 | 3GPP-HD | ✅ |
| 3GPP-HEVC-HDR | HEVC | Main 10 | 4.1 | 3GPP-HDR | ✅ |
| 3GPP-HEVC-UHD | HEVC | Main 10 | 5.1 | 3GPP-UHD | ✅ |
| 3GPP-HEVC-UHD-HDR | HEVC | Main 10 | 5.1 | 3GPP-UHD-HDR | ✅ |
| 3GPP-HEVC-Stereo | HEVC | Main 10 | 5.2 | 3GPP-Stereo | ✅ |
| 3GPP-MV-HEVC-Main-Stereo | MV-HEVC | Multiview Main 10 | 5.1 | 3GPP-Stereo | ✅ |
| 3GPP-MV-HEVC-Ext-Stereo | MV-HEVC | Multiview Extended 10 | 5.1 | 3GPP-Stereo | ✅ |
| 3GPP-AVC-HD | AVC | High Progressive | 4.0 | 3GPP-HD | ✅ |

### AVC HD Requirements (Section 6.2.2)

- Profile: High Progressive (profile_idc = 100)
- Level: 4.0 (level_idc = 40)
- Progressive High: constraint_set4_flag = 1
- Rate constraints (clause 4.5.2):
  - MV range: -2048..2047 (H), -512..511 (V) [recommendation]
  - Max VCL bit rate: 120 Mbps [not yet implemented]
  - Max 16 slices/picture [requirement]
- Representation: 3GPP-HD (clause 4.4.3.2) [not yet implemented]

### HEVC HD Requirements (Section 6.3.2)

- Profile: Main 10 (general_profile_idc = 2)
- Level: 4.1 (general_level_idc = 123)
- Progressive constraints (clause 4.5.3)
- VUI constraints (clause 4.5.3)
- Representation: 3GPP-HD (clause 4.4.3.2)

### HEVC UHD HDR Requirements (Section 6.3.4)

- Profile: Main 10 (general_profile_idc = 2)
- Level: 5.1 (general_level_idc = 153)
- Progressive constraints (clause 4.5.3)
- VUI constraints (clause 4.5.3)
- HDR Colour Space (clause 4.4.3.3):
  - colour_primaries = 9 (BT.2020)
  - transfer_characteristics = 14, 16, or 18
  - matrix_coeffs = 9 (BT.2020 NCL)
  - chroma_sample_loc_type_top_field = 2

## Adding New Operation Points

1. Create XSD schema(s) in `bitstream_rules/`
2. Add operation point to `config.yaml`
3. Test with sample bitstream

## Key Implementation Notes

- XSD 1.1 required for `<xs:assert>` support
- Use `xmlschema.XMLSchema11` for validation
- Indexed elements use `@i`, `@k`, `@j` attributes
- `nuh_layer_id = 0` selects base layer for validation (HEVC only)
- Progressive: `general_progressive_source_flag = 1` (HEVC), `frame_mbs_only_flag = 1` (AVC)
- HDR colour assertions are reusable via `3gpp-hevc-hdr-colour.xsd`
- AVC VUI parameters are nested inside `<VUIParameters>` element
- AVC InternalVariables are nested inside `<SequenceParameterSet>` element
- Rate constraints use `provision="recommendation"` attribute for "should" requirements
- `extract_parameter_value()` returns `(actual_value, is_inferred)` tuple
- `process_parameters()` is kept separate in AVC and HEVC parsers (different handling)

## Current Gaps

- AVC VCL Bit Rate calculation not yet implemented (requires HRD parameters parsing)
- AVC Representation constraints (3GPP-HD) not yet implemented (clause 4.4.3.2)
- No Progressive High profile AVC test bitstream available for end-to-end validation
