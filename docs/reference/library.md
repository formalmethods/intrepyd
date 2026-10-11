# Component library

Reusable building blocks, under `intrepyd.lib`. The package docstring states the
API convention (combinational blocks are functions, stateful blocks are
classes); `eda` holds hardware/EDA blocks and `plc` the IEC 61131-3 function
blocks.

::: intrepyd.lib

## EDA blocks

::: intrepyd.lib.eda

## PLC blocks (IEC 61131-3)

::: intrepyd.lib.plc

## The catalogue

Every block above, described as data for tools (the circuit editor's palette,
`intrepyd.diagram`). `python -m intrepyd.diagram catalogue` prints it as JSON.

::: intrepyd.lib.catalogue
