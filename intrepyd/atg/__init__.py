"""
Automated Test Generation (ATG) for intrepyd.

The entry point is :func:`intrepyd.atg.mcdc.compute_mcdc`, which generates
MC/DC tests for a circuit given as a subclass of
:class:`intrepyd.circuit.Circuit`. See :mod:`intrepyd.atg.mcdc`.
"""

from intrepyd.atg.mcdc import (
    compute_mcdc,
    get_tables_as_dataframe,
    compute_pretty_tables,
)

__all__ = ['compute_mcdc', 'get_tables_as_dataframe', 'compute_pretty_tables']
