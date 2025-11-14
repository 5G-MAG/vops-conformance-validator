"""
    A command-line interface to validate bitstream against SA4 specifications.

    python -m sa4-bitstream-validator --help
"""

__author__ = "Emmanuel Thomas"
__email__  = "thomase@xiaomi.com"

import os
import click
import yaml

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

@cli.command()
@click.argument("bitstream", type=click.Path(exists=True))
@click.argument("operation_point", type=click.STRING)
@click.option("--config", default="config.yaml", help="Path to configuration file")
def check(bitstream, operation_point, config):
    """Check BITSTREAM against a predefined operation point."""
    if not os.path.exists(config):
        click.echo(f"Error: Configuration file '{config}' not found")
        return
    
    # Load configuration
    with open(config, 'r') as f:
        config_data = yaml.safe_load(f)
    
    if not config_data or 'operation_points' not in config_data:
        click.echo("Error: Invalid configuration file format")
        return
    
    if operation_point not in config_data['operation_points']:
        click.echo(f"Error: Operation point '{operation_point}' not found in configuration")
        available_operation_points = list(config_data['operation_points'].keys())
        click.echo(f"Available operation points: {', '.join(available_operation_points)}")
        return
    
    operation_point_config = config_data['operation_points'][operation_point]
    if 'xsds' not in operation_point_config or not operation_point_config['xsds']:
        click.echo(f"Error: Operation point '{operation_point}' has no XSD schemas defined")
        return
    
    # Generate XML filename from bitstream basename
    bitstream_basename = os.path.splitext(os.path.basename(bitstream))[0]
    xml_filename = f"{bitstream_basename}.xml"
    
    click.echo(f"Checking bitstream {bitstream} against operation point '{operation_point}'")
    click.echo(f"Dumping to {xml_filename}")
    
    # Dump bitstream to XML
    with open(bitstream, 'rb') as bs_file:
        with open(xml_filename, 'w') as xml_file:
            parser = HEVCParser()
            parser.bitstream_to_xml(bs_file, xml_file)
    
    # Validate against the operation point's XSDs
    click.echo(f"Validating against {len(operation_point_config['xsds'])} schema(s)")
    validator = XMLValidator()
    validator.validate_multiple(xml_filename, operation_point_config['xsds'])

if __name__ == "__main__":
    cli()
