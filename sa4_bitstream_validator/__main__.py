"""
    A command-line interface to validate bitstream against SA4 specifications.

    python -m sa4-bitstream-validator --help
"""

import os
import click
import yaml

from sa4_bitstream_validator import __version__
from sa4_bitstream_validator.parsers.hevc_parser import HEVCParser
from sa4_bitstream_validator.validators import XMLValidator


def generate_validation_report(results, tested_bitstream, report_path, operation_point=None):
    """Generate a JSON validation report from validation results.
    
    Args:
        results: Validation results from XMLValidator.validate_multiple()
        tested_bitstream: Path to the bitstream file that was validated
        report_path: Path where to save the JSON report
        operation_point: Optional operation point name (for check command)
    """
    import json
    import hashlib
    from datetime import datetime, timezone
    
    # Calculate MD5 hash of the tested bitstream
    try:
        with open(tested_bitstream, 'rb') as f:
            file_hash = hashlib.md5()
            # Read and update hash in chunks of 4K
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)
            md5_hash = file_hash.hexdigest()
    except Exception as e:
        md5_hash = f"error: {str(e)}"
    
    # Create the report structure
    report = {
        "validator_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),  # UTC time
        "bitstream": {
            "path": tested_bitstream,
            "md5": md5_hash
        },
        "operation_point": operation_point,
        "validation_results": {
            "overall_success": results["overall_success"],
            "total_schemas_tested": results["total_schemas"],
            "schemas_passed": results["passed_schemas"],
            "schemas_failed": results["failed_schemas"],
            "schema_details": []
        }
    }
    
    # Note: xml_intermediate is an internal temporary file, not included in the report
    
    # Add detailed schema results with relative paths
    for schema_path, schema_result in results["schema_results"].items():
        # Convert absolute paths to relative paths from project root
        if os.path.isabs(schema_path):
            # Try to make it relative to the project root
            try:
                rel_path = os.path.relpath(schema_path, os.getcwd())
                # If the relative path doesn't start with '..', use it
                if not rel_path.startswith('..'):
                    schema_path = rel_path
            except ValueError:
                # If we can't make it relative, keep the absolute path
                pass
        
        schema_detail = {
            "schema_path": schema_path,  # Use relative path when possible
            "validation_success": schema_result["success"],
            "error_count": schema_result["error_count"],
            "errors": schema_result["errors"]
        }
        report["validation_results"]["schema_details"].append(schema_detail)
    
    # Write the report to file
    try:
        with open(report_path, 'w') as report_file:
            json.dump(report, report_file, indent=2)
        return True, f"Validation report saved to: {report_path}"
    except Exception as e:
        return False, f"Error writing validation report: {e}"

@click.group()
@click.version_option(__version__, "--version", "-v", message="SA4 Bitstream Validator version %(version)s")
@click.pass_context
def cli(ctx):
    """Main command group"""

@cli.command()
@click.argument("bitstream", type=click.File("rb"))
@click.argument("description", type=click.File("w"))
@click.option("--include-internal-vars", is_flag=True, help="Include internal variables in XML dump")
def dump(bitstream, description, include_internal_vars):
    """Dump BITSTREAM in XML format to DESCRIPTION."""
    click.echo(f"Start dumping {bitstream.name} in {description.name}")
    parser = HEVCParser()
    parser.bitstream_to_xml(bitstream, description, include_internal_vars=include_internal_vars)

@cli.command()
@click.argument("description", type=click.Path(exists=True))
@click.argument("xsds", type=click.Path(exists=True), nargs=-1)
def check(description, xsds):
    """Check DESCRIPTION against one or more XSD schemas."""
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
@click.option("--report", "report_path", type=click.Path(), help="Path to JSON validation report file")
@click.option("--include-internal-vars", is_flag=True, help="Include internal variables in XML dump")
def validate(bitstream, operation_point, config, report_path, include_internal_vars):
    """Validate BITSTREAM against a predefined operation point and generate report."""
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
    
    click.echo(f"Validating bitstream {bitstream} against operation point '{operation_point}'")
    click.echo(f"Dumping to {xml_filename}")
    
    # Dump bitstream to XML
    with open(bitstream, 'rb') as bs_file:
        with open(xml_filename, 'w') as xml_file:
            parser = HEVCParser()
            parser.bitstream_to_xml(bs_file, xml_file, include_internal_vars=include_internal_vars)
    
    # Validate against the operation point's XSDs
    click.echo(f"Validating against {len(operation_point_config['xsds'])} schema(s)")
    validator = XMLValidator()
    results = validator.validate_multiple(xml_filename, operation_point_config['xsds'])
    
    # Remove intermediate XML file (internal temporary file)
    try:
        os.remove(xml_filename)
        click.echo(f"Cleaned up intermediate XML file: {xml_filename}")
    except OSError as e:
        click.echo(f"Warning: Could not remove intermediate XML file {xml_filename}: {e}")
    
    # Generate JSON report
    if report_path:
        success, message = generate_validation_report(
            results=results,
            tested_bitstream=bitstream,
            report_path=report_path,
            operation_point=operation_point
        )
        click.echo(message)
    else:
        click.echo("No report file specified. Use --report to generate a validation report.")

if __name__ == "__main__":
    cli()
