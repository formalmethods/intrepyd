# Intrepyd

Intrepyd is a python module that provides a simulator and model checkers in
form of a rich API, to allow the rapid prototyping of **formal methods**
algorithms for the rigorous analysis of circuits, specifications and models.

- Circuits of inputs, latches and combinational nets over booleans, bounded
  and unbounded integers, reals and floats.
- A simulator, and four engines: bounded model checking, k-induction,
  backward reachability and IC3/PDR, whose proofs are checked; a portfolio
  runs them all in parallel, and answers with the first of them.
- Front-ends for Lustre and IEC 61131-3 Structured Text (PLCopen XML).
- Traces as pandas data frames.

```
pip install intrepyd
```

Wheels are available for Linux (x86-64, glibc 2.28 or newer) and Windows
(x86-64), for python 3.11 or newer. Each one carries the intrepid model
checking library for its platform, so there is nothing else to install.

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ctx = ip.Context()
int8_t = ctx.mk_int8_type()
c = ctx.mk_latch('c', int8_t)
ctx.set_latch_init_next(c, ctx.mk_number('0', int8_t),
                        ctx.mk_add(c, ctx.mk_number('1', int8_t)))

bmc = ctx.mk_bmc()
bmc.add_target(ctx.mk_eq(c, ctx.mk_number('5', int8_t)))
bmc.set_current_depth(5)
assert bmc.reach_targets() == EngineResult.REACHABLE
```

The documentation, the source and the issue tracker are on
[GitHub](https://github.com/formalmethods/intrepyd); a collection of
experiences using Intrepyd is in the
[Formal Methods Little Corner](https://formalmethods.github.io).

Intrepyd is released under the BSD 3-Clause license. The intrepid library
bundled in the wheels is proprietary, and its license, installed as
`intrepyd/LICENSE.intrepid`, allows it to be used and redistributed freely,
unmodified, as part of intrepyd. It links the Z3 SMT solver, released under
the MIT license.
