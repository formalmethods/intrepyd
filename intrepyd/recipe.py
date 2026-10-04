"""
This module implements the recipe of a context: the record of the calls that
built its circuit, which can be replayed to build the same circuit in a new
context, typically in another process, where the nets of the original context
mean nothing. The portfolio (intrepyd.portfolio) uses it to run each engine
in a process of its own.

Every Context records its recipe as it goes. The nets of the original context
are recorded as references to the calls that made them, and its types and
predefined nets (true, false, undef) by name, so that replaying the calls in
order rebuilds every net, with the same names.
"""

# The attributes of a Context that hold its types, and its predefined nets
TYPE_ATTRIBUTES = ('booleantype', 'int8type', 'int16type', 'int32type', 'int64type',
                   'uint8type', 'uint16type', 'uint32type', 'uint64type', 'realtype',
                   'float16type', 'float32type', 'float64type', 'inttype')
NET_ATTRIBUTES = ('undef', 'true', 'false')


class Recipe:
    """
    The calls that built the circuit of a context
    """

    def __init__(self, context):
        # (method name, arguments, keyword arguments), with every net and type
        # replaced by a reference
        self.calls = []
        self._refs = {net: ('attr', name)
                      for name in NET_ATTRIBUTES
                      for net in [getattr(context, name)]}
        self._types = {getattr(context, name): name for name in TYPE_ATTRIBUTES}
        # The first value passed as a net that the recipe does not know: a net
        # built bypassing the context, e.g. through intrepyd.api directly
        self._unknown = None
        self.enabled = True

    def record(self, name, args, kwargs, result):
        """
        Records a call of a method of the context, and the net it returned
        """
        if not self.enabled:
            return
        self.calls.append((name,
                           tuple(self._reference(arg) for arg in args),
                           {key: self._reference(value) for key, value in kwargs.items()}))
        if isinstance(result, int):
            self._refs[result] = ('net', len(self.calls) - 1)

    def ref(self, net):
        """
        Returns the reference of a net of the context, which replay() resolves
        to the same net in the replayed context
        """
        if net not in self._refs:
            raise ValueError('Net %s was not built through the context, so it cannot be '
                             'rebuilt in another context' % net)
        return self._refs[net]

    def check(self):
        """
        Raises ValueError if the recipe cannot rebuild the circuit
        """
        if self._unknown is not None:
            raise ValueError('The circuit uses net %s, which was not built through the '
                             'context, so it cannot be rebuilt in another context'
                             % self._unknown)

    def _reference(self, value):
        if isinstance(value, int) and not isinstance(value, bool):
            if value in self._refs:
                return self._refs[value]
            if value in self._types:
                return ('attr', self._types[value])
            if self._unknown is None:
                self._unknown = value
        return ('value', value)


def replay(calls, context):
    """
    Builds the circuit of the calls of a recipe in context, a new Context.
    Returns a function that maps a reference (see Recipe.ref) to its net in
    context.
    """
    context.recipe.enabled = False
    results = []

    def resolve(reference):
        kind, value = reference
        if kind == 'net':
            return results[value]
        if kind == 'attr':
            return getattr(context, value)
        return value

    for name, args, kwargs in calls:
        method = getattr(context, name)
        results.append(method(*[resolve(arg) for arg in args],
                              **{key: resolve(value) for key, value in kwargs.items()}))
    return resolve
