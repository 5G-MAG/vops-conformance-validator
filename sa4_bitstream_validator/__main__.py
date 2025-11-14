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
@click.argument("xsds", type=click.Path(exists=True), nargs=-1)
def validate(description, xsds):
    """Validate DESCRIPTION against one or more XSD schemas."""
    if not xsds:
        click.echo("Error: At least one XSD schema must be provided")
        return
        
    click.echo(f"Start validation of {description} against {len(xsds)} schema(s)")
    validator = XMLValidator()
    validator.validate_multiple(description, xsds)

if __name__ == "__main__":
    cli()
