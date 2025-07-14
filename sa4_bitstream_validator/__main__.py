"""
    A command-line interface to validate bitstream against SA4 specifications.

    python -m sa4-bitstream-validator --help
"""

__author__ = "Emmanuel Thomas"
__email__  = "thomase@xiaomi.com"

import click

from sa4_bitstream_validator.parsers.hevc_parser import HEVCParser
from sa4_bitstream_validator.validators import XMLValidator

@click.group()
@click.pass_context
def cli(ctx):
    """Main command group"""

@cli.command()
@click.argument("bitstream", type=click.File("rb"))
@click.argument("description", type=click.File("w"))
def dump(bitstream, description):
    """Dump BITSTREAM in XML format to DESCRIPTION."""
    click.echo(f"Start dumping {bitstream.name} in {description.name}")
    parser = HEVCParser()
    parser.bitstream_to_xml(bitstream, description)

@cli.command()
@click.argument("description", type=click.Path(exists=True))
@click.argument("op", type=click.Path(exists=True))
def validate(description, op):
    """Validate BITSTREAM against the OP."""
    click.echo(f"Start validation of {description} against {op}")
    validator = XMLValidator()
    validator.validate(description, op)

if __name__ == "__main__":
    cli()
