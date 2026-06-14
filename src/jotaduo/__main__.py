# -*- coding: utf-8 -*-
"""Allow running JotaDuo via ``python -m jotaduo``."""
from .cli.main import cli

if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
