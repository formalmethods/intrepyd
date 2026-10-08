# Running as a service

Intrepyd also runs as a REST service, served by gunicorn in a Docker image:

```bash
docker run -p 8000:8000 ghcr.io/formalmethods/intrepid-server
```

!!! info "The service is a project of its own"
    The service, its REST API and its Docker image live in
    [intrepid-server](https://github.com/formalmethods/intrepid-server), which
    installs intrepyd from PyPI and is released on its own schedule. Its
    documentation belongs there; this page covers only how a python program
    uses it through intrepyd.

A python program can use the service exactly as it uses intrepyd: after
[`use_remote()`](../reference/remote.md), every `Context` is a context on the
service, with the same methods, each of which becomes the equivalent REST call.

```python
import intrepyd as ip
from intrepyd.engine import EngineResult

ip.use_remote('http://127.0.0.1:8000')   # from now on, contexts are remote

ctx = ip.Context()
bool_t = ctx.mk_boolean_type()
a = ctx.mk_input('a', bool_t)
b = ctx.mk_input('b', bool_t)
bmc = ctx.mk_bmc()
bmc.add_target(ctx.mk_and(a, b))
bmc.add_watch(a)
bmc.add_watch(b)
bmc.set_current_depth(0)
assert bmc.reach_targets() == EngineResult.REACHABLE
print(bmc.get_last_trace().get_as_dataframe(ctx.net2name))

ip.use_local()                           # and local again
```

Engines, the portfolio, traces and simulators work as they do locally, with the
same results; a failed call raises `intrepyd.RemoteError`.
`ip.RemoteContext(url)` makes a remote context whatever the mode.

What differs: nets are `intrepyd.remote.Net` objects, named as in
`ctx.net2name`, rather than ints; types are the names of the REST API
(`'bool'`, `'int8'`, ...); each call is a round trip to the service, so
building large models is slower than locally; and the service deletes the
context once the `RemoteContext` is garbage collected. It needs
intrepid-server 1.1.0 or newer.
