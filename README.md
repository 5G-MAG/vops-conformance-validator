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
$ python -m sa4_bitstream_validator dump bitstream_path description.xml

$ python -m sa4_bitstream_validator validate description.xml bitstream_rules/operation_point.xsd
```

## Help

```shell
$ python -m sa4_bitstream_validator --help
Usage: python -m sa4_bitstream_validator [OPTIONS] COMMAND [ARGS]...

  Main command group

Options:
  --help  Show this message and exit.

Commands:
  dump      Dump BITSTREAM in XML format to DESCRIPTION.
  validate  Validate BITSTREAM against the OP.
```

## License
See `LICENSE` file.

## Project status
In development as part of the VOPS Work Item.
