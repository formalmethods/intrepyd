# Diagram

Builds, simulates and verifies a circuit drawn as a diagram, and generates
MC/DC tests for it ([guide](../guide/test-generation.md#from-a-circuit-diagram)): the documents
(`*.intrepyd.json`) of the intrepid-vscode circuit editor. It is the inverse of
[`intrepyd.export`](export.md): a netlist back into a
[`Context`](context.md), ready for the [`Simulator`](simulator.md). The module
docstring below describes the diagram format (sub-systems included) and the
command line. The library blocks a diagram may use are those of the
[catalogue](library.md#the-catalogue).

::: intrepyd.diagram
