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
- **SEI Support**: Parsing of Supplemental Enhancement Information, including three-dimensional reference displays info
- **Assertion Reporting**: Detailed reporting of all passing and failing XSD assertions
- **Multiple Schema Validation**: Validation against multiple XSD schemas in a single operation
- **JSON Reports**: Comprehensive validation reports with assertion details

## Supported Operation Points

- `3GPP-MV-HEVC-Main-Stereo` - MV-HEVC stereo bitstream validation with VUI, progressive, and stereo constraints

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
