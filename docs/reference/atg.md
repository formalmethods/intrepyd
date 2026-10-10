# Automated test generation

Generates MC/DC (Modified Condition / Decision Coverage) tests for a circuit.
The circuit is a [`Circuit`](circuit.md) subclass that registers its decision
and condition nets by name in `self.nets`; `compute_mcdc` builds it twice and
searches, with the engines, for the independence pair of each condition.

::: intrepyd.atg.mcdc
    options:
      members:
        - compute_mcdc
        - get_tables_as_dataframe
        - compute_pretty_tables
