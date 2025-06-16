"""A command-line interface to validate bitstream against SA4 specifications.

    python -m sa4-bitstream-validator --help
"""

import click

@click.command()
@click.argument("bitstream", type=click.File("rb"))
@click.argument("op")
def validate(bitstream, op):
    """Validate BITSTREAM against the OP."""
    click.echo(f"Start validation of {bitstream} against {op}")
    click.echo("Not implemented !")

if __name__ == "__main__":
    validate()
