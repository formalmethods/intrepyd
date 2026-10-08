# Portfolio

The engines are complementary: BMC finds counterexamples fastest, and
k-induction, backward reachability and PDR each prove properties the others
cannot. [`mk_portfolio()`](../reference/portfolio.md) runs them all at the same
time, and stops them as soon as one gives a conclusive answer.

```python
portfolio = ctx.mk_portfolio()          # or engines=('kind', 'pdr'), max_depth=50
portfolio.add_target(bad)
portfolio.add_watch(c)
result = portfolio.reach_targets(timeout=60)
print(result, portfolio.get_last_engine(), portfolio.get_last_time())
if result == EngineResult.REACHABLE:
    print(portfolio.get_last_trace().get_as_dataframe(ctx.net2name))
```

The engines are `bmc`, `kind` (k-induction), `br` (backward reachability) and
`pdr`, all of them by default; `max_depth` bounds the depths that `bmc` and
`kind` try, which are unbounded by default. `reach_targets()` returns the first
`REACHABLE` or `UNREACHABLE` answer, or `UNKNOWN` if every engine gives up or
`timeout` seconds pass first; `get_last_engine()` says which engine answered,
and `get_last_errors()` reports the engines that failed.

## How it runs

Each engine runs in a process of its own, so the portfolio uses as many cores
as engines, and stopping the others is immediate. Each process builds the
circuit again from the *recipe* of the context: every context records the calls
that build its circuit, so a circuit must be built through the methods of
[`Context`](../reference/context.md) (as the Lustre and Structured Text
translators and the parser do), not through `intrepyd.api` directly. The
counterexample of a `REACHABLE` answer is rebuilt in the caller's context, by
BMC at the depth the engine found, the first time `get_last_trace()` is called.

!!! warning "Guard the entry point"
    The processes are started with `multiprocessing`, which imports the main
    module of the program in each of them: a script that uses a portfolio must
    keep its top-level code under `if __name__ == '__main__':`.
