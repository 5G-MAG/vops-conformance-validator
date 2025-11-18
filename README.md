# sa4-bitstream-validator

## Name
SA4 Bitstream Validator

## Description
The SA4 bitstream validator verifies that a input video bitstream conforms to a given operation point defined in the VOPS specification.


## Installation

```shell
python -m pip install -r requirements.txt
```

## Usage

```shell
# Dump bitstream to XML format
$ python -m sa4_bitstream_validator dump bitstream_path description.xml

# Validate XML description against XSD schemas
$ python -m sa4_bitstream_validator validate description.xml bitstream_rules/operation_point.xsd

# Check bitstream against predefined operation point (combines dump + validate)
$ python -m sa4_bitstream_validator check bitstream_path operation_point_name
```

## Help

```shell
$ python -m sa4_bitstream_validator --help
Usage: python -m sa4_bitstream_validator [OPTIONS] COMMAND [ARGS]...

  Main command group

Options:
  -v, --version  Show the version and exit.
  --help         Show this message and exit.

Commands:
  check     Check BITSTREAM against a predefined operation point.
  dump      Dump BITSTREAM in XML format to DESCRIPTION.
  validate  Validate DESCRIPTION against one or more XSD schemas.
```

## License
See `LICENSE` file.

## Project status
In development as part of the VOPS Work Item.
