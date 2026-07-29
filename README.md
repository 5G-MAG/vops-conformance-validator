# sa4-bitstream-validator

## Name
SA4 Bitstream Validator

## Description
The SA4 bitstream validator verifies that an input video bitstream conforms to a given operation point defined in the VOPS specification. The tool supports HEVC bitstream validation with comprehensive assertion reporting.

## Installation

```shell
python -m pip install -r requirements.txt
```

## Usage

```shell
# Dump bitstream to XML format
$ python -m sa4_bitstream_validator dump bitstream_path description.xml

# Dump bitstream with internal variables included
$ python -m sa4_bitstream_validator dump bitstream_path description.xml --include-internal-vars

# Check XML description against XSD schemas (console output only)
$ python -m sa4_bitstream_validator check description.xml bitstream_rules/3gpp-mv-hevc_stereo.xsd

# Validate bitstream against predefined operation point with JSON report
$ python -m sa4_bitstream_validator validate bitstream_path 3GPP-MV-HEVC-Main-Stereo --report report.json

# Validate without report (console output only, cleans up intermediate files)
$ python -m sa4_bitstream_validator validate bitstream_path 3GPP-MV-HEVC-Main-Stereo

# Validate with internal variables included
$ python -m sa4_bitstream_validator validate bitstream_path 3GPP-MV-HEVC-Main-Stereo --include-internal-vars
```

## Features

- **HEVC Bitstream Parsing**: Comprehensive parsing of HEVC bitstreams including VPS, SPS, PPS, and SEI messages
- **AVC Bitstream Parsing**: Comprehensive parsing of AVC bitstreams including SPS, PPS, and slice headers
- **SEI Support**: Parsing of Supplemental Enhancement Information, including three-dimensional reference displays info
- **Assertion Reporting**: Detailed reporting of all passing and failing XSD assertions
- **Multiple Schema Validation**: Validation against multiple XSD schemas in a single operation
- **JSON Reports**: Comprehensive validation reports with assertion details
- **Recommendation Support**: Distinguishes between "shall" (error) and "should" (warning) requirements

## Supported Operation Points

| Operation Point | Codec | Status | Tested |
|-----------------|-------|--------|--------|
| `3GPP-AVC-HD` | AVC | Implemented | Needs testing with Progressive High profile bitstream |
| `3GPP-HEVC-HD` | HEVC | Implemented | ✅ |
| `3GPP-HEVC-HDR` | HEVC | Implemented | ✅ |
| `3GPP-HEVC-UHD` | HEVC | Implemented | ✅ |
| `3GPP-HEVC-UHD-HDR` | HEVC | Implemented | ✅ |
| `3GPP-HEVC-Stereo` | HEVC | Implemented | ✅ |
| `3GPP-MV-HEVC-Main-Stereo` | MV-HEVC | Implemented | ✅ |
| `3GPP-MV-HEVC-Ext-Stereo` | MV-HEVC | Implemented | ✅ |

> **Note**: All operation points need to be tested with their respective conformance bitstreams. "Implemented" means the XSD schemas and parser support exist, but validation against actual bitstreams may reveal issues.

## Help

```shell
$ python -m sa4_bitstream_validator --help
Usage: python -m sa4_bitstream_validator [OPTIONS] COMMAND [ARGS]...

  Main command group

Options:
  -v, --version  Show the version and exit.
  --help         Show this message and exit.

Commands:
  check     Check DESCRIPTION against one or more XSD schemas.
  dump      Dump BITSTREAM in XML format to DESCRIPTION.
  validate  Validate BITSTREAM against a predefined operation point and generate report.

$ python -m sa4_bitstream_validator validate --help
Usage: python -m sa4_bitstream_validator validate [OPTIONS] BITSTREAM OPERATION_POINT

  Validate BITSTREAM against a predefined operation point and generate report.

Options:
  --config TEXT            Path to configuration file
  --report PATH            Path to JSON validation report file
  --include-internal-vars  Include internal variables in XML dump
  --help                   Show this message and exit.

$ python -m sa4_bitstream_validator dump --help
Usage: python -m sa4_bitstream_validator dump [OPTIONS] BITSTREAM DESCRIPTION

  Dump BITSTREAM in XML format to DESCRIPTION.

Options:
  --include-internal-vars  Include internal variables in XML dump
  --help                   Show this message and exit.
```

## License
See `LICENSE` file.

## Project status
In development as part of the VOPS Work Item.

---

## For Maintainers

### Design Principles

1. **Bitstream → XML → Validation Pipeline**: The tool first converts bitstreams to a structured XML representation, then validates the XML against XSD schemas. This separation allows:
   - Reuse of parsed XML for multiple validations
   - Debugging by inspecting the intermediate XML
   - Clear separation between parsing and validation logic

2. **Template Method Pattern**: The `BaseParser` class provides a shared `bitstream_to_xml()` template method. Codec-specific parsers (AVC, HEVC) implement abstract methods for:
   - NAL header parsing
   - Payload dispatching
   - Codec-specific parameter handling

3. **XSD 1.1 for Assertions**: Uses `<xs:assert>` elements for conformance checks. This allows:
   - Declarative constraint definitions
   - Reusable schema components
   - Standard XPath expressions for validation

4. **Separation of Concerns**:
   - Parsers (`parsers/`) generate XML from bitstreams
   - Validators (`validators.py`) check XML against schemas
   - Schemas (`bitstream_rules/`) define conformance constraints
   - Config (`config.yaml`) maps operation points to schemas

### Validation Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Bitstream  │────▶│   Parser    │────▶│    XML      │────▶│  Validator  │
│  (.264/.hevc)│     │ (AVC/HEVC)  │     │  Document   │     │ (XSD 1.1)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                    │
                                                    ▼
                                            ┌─────────────┐
                                            │  XSD Schemas│
                                            │ (operation  │
                                            │  point)     │
                                            └─────────────┘
```

**Step 1: Parse Bitstream**
- Read NAL units from bitstream
- Parse NAL headers (1 byte for AVC, 2 bytes for HEVC)
- Dispatch to codec-specific parsers (SPS, PPS, VPS, SEI, Slice)
- Extract parameters and compute internal variables

**Step 2: Generate XML**
- Create XML elements for each NAL unit
- Nest parameters according to codec structure
- Include internal variables (e.g., MaxPictureSliceCount)
- Serialize to pretty-printed XML

**Step 3: Load XSD Schemas**
- Read operation point from `config.yaml`
- Load XSD schemas specified for the operation point
- Support AND logic (all schemas must pass)
- Support OR logic (list of schemas where one must pass)

**Step 4: Validate**
- Run XSD validation against each schema
- Extract assertion results (pass/fail)
- Generate validation report
- Clean up intermediate files

### XSD Schema Structure

Schemas use XSD 1.1 with `<xs:assert>` for conformance checks:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:vc="http://www.w3.org/2007/XMLSchema-versioning"
  elementFormDefault="qualified"
  attributeFormDefault="unqualified"
  vc:minVersion="1.1">

  <!-- Include common type definitions -->
  <xs:include schemaLocation="hevc_common.xsd"/>

  <xs:element name="HEVCBitstream">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="NALUnit" maxOccurs="unbounded"/>
      </xs:sequence>

      <!-- SHALL assertions (default) - validator reports as error if fails -->
      <xs:assert test="NALUnit[nuh_layer_id=0]/SequenceParameterSet/general_profile_idc = 2"/>

      <!-- SHOULD assertions (recommendation) - validator reports as warning if fails -->
      <xs:assert test="..." provision="recommendation"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

**Key Points:**
- Use `vc:minVersion="1.1"` for XSD 1.1 support
- Include common type definitions from `{codec}_common.xsd`
- Use `provision="recommendation"` for "should" requirements (validator reports as warning)
- Default is `provision="requirement"` for "shall" requirements (validator reports as error)
- The validator strips the `provision` attribute before passing to `xmlschema` library

### Adding a New Video Codec

#### Step 1: Create Parser Module

Create directory structure:
```
sa4_bitstream_validator/parsers/
├── {codec}_parser.py        # Main parser class
└── {codec}/                 # Codec-specific parsing modules
    ├── __init__.py
    ├── sps.py               # Sequence Parameter Set parser
    ├── pps.py               # Picture Parameter Set parser
    └── ...                  # Other NAL unit parsers
```

#### Step 2: Implement Parser Class

Extend `BaseParser` and implement abstract methods:

```python
from sa4_bitstream_validator.parsers.base_parser import (
    BaseParser,
    extract_parameter_value,
    create_indexed_element,
    create_regular_element,
    create_internal_variables_element
)

class NewCodecParser(BaseParser):
    def get_codec_name(self):
        """Return codec name for XML root element."""
        return "NEWCODEC"
    
    def nal_header_size(self):
        """Return NAL header size in bytes."""
        return 2  # or 1 for AVC-like codecs
    
    def parse_nal_header(self, header_bytes):
        """Parse NAL header; return dict of header fields."""
        return {
            'forbidden_zero_bit': ...,
            'nal_unit_type': ...,
            # ... other fields
        }
    
    def write_nal_header_to_xml(self, nal_unit, parsed_header):
        """Write NAL header fields as XML elements."""
        SubElement(nal_unit, "forbidden_zero_bit").text = str(parsed_header['forbidden_zero_bit'])
        SubElement(nal_unit, "nal_unit_type").text = str(parsed_header['nal_unit_type'])
        # ... other fields
    
    def parse_nal_payload(self, parsed_header, data, payload_start, end_pos, 
                          nal_unit, include_internal_vars):
        """Dispatch to codec-specific parsers."""
        nal_type = parsed_header['nal_unit_type']
        
        if nal_type == SPS_TYPE:
            # Parse SPS and add to XML
            pass
        elif nal_type == PPS_TYPE:
            # Parse PPS and add to XML
            pass
        # ... other NAL types
```

#### Step 3: Implement Parameter Processing

Create a `process_parameters()` function specific to your codec:

```python
def process_parameters(parent_elem, parameters, include_internal_vars=False):
    """Process parameters and create XML elements."""
    internal_vars = []
    
    for key, value in parameters.items():
        if not include_internal_vars and key.startswith("_"):
            continue
        
        xml_key = key[1:] if key.startswith("_") and include_internal_vars else key
        
        if key.startswith("_") and include_internal_vars:
            internal_vars.append((xml_key, value))
        elif isinstance(value, dict):
            # Handle nested structures (e.g., VUI parameters)
            nested_elem = SubElement(parent_elem, xml_key)
            nested_vars = process_parameters(nested_elem, value, include_internal_vars)
            if nested_vars:
                create_internal_variables_element(nested_elem, nested_vars)
        else:
            actual_value, _ = extract_parameter_value(value)
            indexed_elem = create_indexed_element(parent_elem, xml_key, actual_value)
            if indexed_elem is None:
                create_regular_element(parent_elem, xml_key, actual_value)
    
    return internal_vars
```

#### Step 4: Create Common XSD Types

Create `bitstream_rules/{codec}_common.xsd` with type definitions:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" ...>
  
  <!-- Indexed types -->
  <xs:complexType name="IndexedIntegerType">
    <xs:simpleContent>
      <xs:extension base="xs:integer">
        <xs:attribute name="i" type="xs:nonNegativeInteger" use="optional"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
  
  <!-- NAL unit type -->
  <xs:element name="NALUnit" type="NALUnitType"/>
  <xs:complexType name="NALUnitType">
    <xs:sequence>
      <xs:element name="startCode" type="xs:string"/>
      <xs:element name="nal_unit_type" type="xs:integer"/>
      <!-- ... other header fields -->
      <xs:choice minOccurs="0">
        <xs:element name="SequenceParameterSet" type="SPSType"/>
        <xs:element name="PictureParameterSet" type="PPSType"/>
      </xs:choice>
    </xs:sequence>
  </xs:complexType>
  
  <!-- SPS type -->
  <xs:complexType name="SPSType">
    <xs:sequence>
      <xs:element name="profile_idc" type="xs:integer"/>
      <!-- ... other SPS fields -->
      <xs:element name="InternalVariables" type="InternalVariablesType" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>
  
  <!-- Internal variables type -->
  <xs:complexType name="InternalVariablesType">
    <xs:sequence>
      <xs:element name="MaxPictureSliceCount" type="xs:integer" minOccurs="0"/>
      <!-- ... other internal variables -->
    </xs:sequence>
  </xs:complexType>
</xs:schema>
```

#### Step 5: Add Codec Detection

Update `sa4_bitstream_validator/__main__.py` to detect and use the new codec:

```python
from sa4_bitstream_validator.parsers.newcodec_parser import NewCodecParser

# In the dump command:
if codec == "newcodec":
    parser = NewCodecParser()

# In the validate command:
if "NEWCODEC" in operation_point.upper():
    parser = NewCodecParser()
```

### Adding a New Operation Point

#### Step 1: Create XSD Schemas

Create one or more XSD files in `bitstream_rules/`:

```xml
<!-- bitstream_rules/3gpp-newcodec-op.xsd -->
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema ...>
  <xs:include schemaLocation="newcodec_common.xsd"/>
  
  <xs:element name="NewCodecBitstream">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="NALUnit" maxOccurs="unbounded"/>
      </xs:sequence>
      
      <!-- Profile assertion -->
      <xs:assert test="NALUnit/SequenceParameterSet/profile_idc = 100"/>
      
      <!-- Level assertion -->
      <xs:assert test="NALUnit/SequenceParameterSet/level_idc = 40"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

#### Step 2: Add to config.yaml

```yaml
operation_points:
  3GPP-NEWCODEC-HD:
    description: "3GPP NewCodec HD Operation Point"
    xsds:
      - bitstream_rules/3gpp-newcodec-op.xsd
      - bitstream_rules/3gpp-newcodec-rate-constraints.xsd
```

#### Step 3: Test with Sample Bitstream

```bash
# Dump bitstream to XML
python -m sa4_bitstream_validator dump test_files/sample.newcodec output.xml --codec newcodec

# Validate against operation point
python -m sa4_bitstream_validator validate test_files/sample.newcodec 3GPP-NEWCODEC-HD

# Generate JSON report
python -m sa4_bitstream_validator validate test_files/sample.newcodec 3GPP-NEWCODEC-HD --report report.json
```

### Key Implementation Notes

- **XSD 1.1 required**: Use `<xs:assert>` with `vc:minVersion="1.1"`
- **xmlschema library**: Use `xmlschema.XMLSchema11` for validation
- **Indexed elements**: Use `@i`, `@k`, `@j` attributes (e.g., `field[i=3]`)
- **Layer selection**: `nuh_layer_id = 0` selects base layer (HEVC only)
- **Progressive flags**: `general_progressive_source_flag = 1` (HEVC), `frame_mbs_only_flag = 1` (AVC)
- **Reusable schemas**: HDR colour assertions in `3gpp-hevc-hdr-colour.xsd`
- **VUI nesting**: AVC VUI parameters are nested inside `<VUIParameters>` element
- **Internal variables**: AVC InternalVariables are nested inside `<SequenceParameterSet>` element
- **Recommendations**: Use `provision="recommendation"` for "should" requirements
- **Value extraction**: `extract_parameter_value()` returns `(actual_value, is_inferred)` tuple
- **Parameter processing**: `process_parameters()` is codec-specific (different handling for AVC vs HEVC)
