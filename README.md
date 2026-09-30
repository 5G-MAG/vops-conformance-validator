<p align="center">
  <img src=".github/banner.svg" width="100%" alt="Testbeds · Video Capabilities and Operation Points: VOPS Conformance Validator">
</p>

<p align="center">
  Checks that an AVC or HEVC video bitstream conforms to an operation point defined in
  3GPP TS 26.265.
</p>

<p align="center">
  <img alt="Status: under development"
    src="https://img.shields.io/badge/Status-Under%20Development-e67e22">
  <a href="https://github.com/5G-MAG/vops-conformance-validator/releases"><img alt="Version"
    src="https://img.shields.io/github/v/release/5G-MAG/vops-conformance-validator?label=Version&sort=semver"></a>
  <a href="LICENSE"><img alt="License: BSD 3-Clause Clear"
    src="https://img.shields.io/badge/License-BSD%203--Clause%20Clear-blue"></a>
</p>

<p align="center">
  <a href="https://www.5g-mag.com/testbeds">Testbeds</a> &nbsp;&middot;&nbsp;
  <a href="https://github.com/5G-MAG/vops-conformance-validator/issues">Issues</a> &nbsp;&middot;&nbsp;
  <a href="https://www.5g-mag.com/contributing">Contributing</a>
</p>

---

## At a glance

|  |  |
|---|---|
| **Validates against** | 3GPP TS 26.265 V19.2.0 (2026-03), *Media Delivery: Video Capabilities and Operation Points* (Release 19) |
| **Codecs** | AVC, HEVC, MV-HEVC |
| **Built with** | Python: bitstring, click, xmlschema, PyYAML (see `requirements.txt`) |
| **Part of** | [Testbeds & Evaluation Frameworks](https://www.5g-mag.com/testbeds) |

## Introduction

The validator verifies that an input video bitstream conforms to a given operation point defined
in the VOPS specification, 3GPP TS 26.265. It parses the bitstream into an XML description, then
checks that description against XSD 1.1 schemas, one set per operation point, and reports every
passing and failing assertion.

TS 26.265 V19.2.0, clause B.2.3: "A conformance validator for testing bitstreams for conformance against the operation points defined in this specification is provided".

It is a conformance tool, not an implementation of the specification: it tests bitstreams produced
by encoders, and does not encode or decode video.

### Features

- **HEVC Bitstream Parsing**: Comprehensive parsing of HEVC bitstreams including VPS, SPS, PPS, and SEI messages
- **AVC Bitstream Parsing**: Comprehensive parsing of AVC bitstreams including SPS, PPS, and slice headers
- **SEI Support**: Parsing of Supplemental Enhancement Information, including three-dimensional reference displays info
- **Assertion Reporting**: Detailed reporting of all passing and failing XSD assertions
- **Multiple Schema Validation**: Validation against multiple XSD schemas in a single operation
- **JSON Reports**: Comprehensive validation reports with assertion details
- **Recommendation Support**: Distinguishes between "shall" (error) and "should" (warning) requirements

## Specification

Built against **3GPP TS 26.265 V19.2.0 (2026-03)**, the version recorded in the `REFERENCE` file.

TS 26.265 V19.2.0, clause B.2.3: "The detailed semantics and the format of the report is for further study." The JSON report format used here is therefore this tool's own, not one the
specification defines.

### Supported operation points

| Operation Point | Codec | Status | Tested |
|-----------------|-------|--------|--------|
| `3GPP-AVC-HD` | AVC | Implemented | Needs testing|
| `3GPP-HEVC-HD` | HEVC | Implemented | Needs testing |
| `3GPP-HEVC-HDR` | HEVC | Implemented | Needs testing |
| `3GPP-HEVC-UHD` | HEVC | Implemented | Needs testing |
| `3GPP-HEVC-UHD-HDR` | HEVC | Implemented | Needs testing |
| `3GPP-HEVC-Stereo` | HEVC | Implemented | Needs testing |
| `3GPP-MV-HEVC-Main-Stereo` | MV-HEVC | Implemented | Needs testing |
| `3GPP-MV-HEVC-Ext-Stereo` | MV-HEVC | Implemented | Needs testing |

> **Note**: All operation points need to be tested with their respective conformance bitstreams. "Implemented" means the XSD schemas and parser support exist, but validation against actual bitstreams may reveal issues.

## Install dependencies

```shell
python -m pip install -r requirements.txt
```

## Downloading

```bash
cd ~
git clone https://github.com/5G-MAG/vops-conformance-validator.git
cd vops-conformance-validator
```

## Running

```shell
# Dump bitstream to XML format
$ python -m sa4_bitstream_validator dump bitstream_path description.xml

# Dump bitstream with internal variables included
$ python -m sa4_bitstream_validator dump bitstream_path description.xml --include-internal-vars

# Dump AVC bitstream to XML format
$ python -m sa4_bitstream_validator dump bitstream_path description.xml --codec avc

# Check XML description against XSD schemas (console output only)
$ python -m sa4_bitstream_validator check description.xml bitstream_rules/3gpp-mv-hevc_stereo.xsd

# Validate bitstream against predefined operation point with JSON report
$ python -m sa4_bitstream_validator validate bitstream_path 3GPP-MV-HEVC-Main-Stereo --report report.json

# Validate without report (console output only, cleans up intermediate files)
$ python -m sa4_bitstream_validator validate bitstream_path 3GPP-MV-HEVC-Main-Stereo

# Validate with internal variables included
$ python -m sa4_bitstream_validator validate bitstream_path 3GPP-MV-HEVC-Main-Stereo --include-internal-vars

# Validate AVC bitstream against operation point (codec auto-detected)
$ python -m sa4_bitstream_validator validate bitstream_path 3GPP-AVC-HD --report report.json
```

### Command reference

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

> **Note**: The validate command auto-detects the codec based on the operation point name. Operation points starting with "3GPP-AVC" use the AVC parser, all others use the HEVC parser.

$ python -m sa4_bitstream_validator dump --help
Usage: python -m sa4_bitstream_validator dump [OPTIONS] BITSTREAM DESCRIPTION

  Dump BITSTREAM in XML format to DESCRIPTION.

Options:
  --include-internal-vars  Include internal variables in XML dump
  --codec [hevc|avc]       Codec type (default: hevc)
  --help                   Show this message and exit.
```

## Configuration

`config.yaml` maps each operation point to the XSD schemas in `bitstream_rules/` that a bitstream
must pass. See [Adding a New Operation Point](#adding-a-new-operation-point) below.

## Development

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
┌──────────────┐     ┌──────────────┐     ┌─────────────┐      ┌─────────────┐
│  Bitstream   │────▶│   Parser    │────▶│    XML      │────▶│  Validator  │
│  (.264/.hevc)│     │ (AVC/HEVC)   │     │  Document   │      │ (XSD 1.1)   │
└──────────────┘     └──────────────┘     └─────────────┘      └─────────────┘
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

## Contributing

Contributions are welcome. How to raise an issue, fork the repository and open a pull request, and
the Contributor License Agreement required before code can be merged, are described at
<https://www.5g-mag.com/contributing>.

## License

Distributed under the Clear BSD License, copyright 3GPP Organizational Partners (ARIB, ATIS, CCSA,
ETSI, TSDSI, TTA, TTC). See [LICENSE](LICENSE).

## Acknowledgements

This repository is a mirror of work started in 3GPP SA4 in the context of the VOPS work item,
3GPP TS 26.265, originally hosted at
<https://forge.3gpp.org/rep/sa4/ts-26.265/conformance/bitstream-validator>. Thanks to the original
author, listed in [AUTHORS](AUTHORS).
