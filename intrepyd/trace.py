"""
This module implements the class for traces
"""

from fractions import Fraction
from pandas import DataFrame
from intrepyd.api import mk_trace, trace_get_max_depth, trace_get_watched_net, \
                         trace_prepare_value_for_net, trace_set_value, value_at, \
                         trace_get_watched_nets_number

class Trace:
    """
    A trace generated from an Engine, or manually built for use in simulation
    """
    def __init__(self, ctx, rawtrace=None):
        self.ctx = ctx
        self.rawtrace = None
        if rawtrace is None:
            rawtrace = mk_trace(self.ctx)
        self.rawtrace = rawtrace

    @staticmethod
    def get_numeric_value(value):
        """
        Converts a string value (including true, false) into a corresponding float or integer.
        Reals that are not finite decimals come as fractions, n/d, and floats can be inf,
        -inf and nan.
        """
        if value == '?':
            return '?'
        if value == 'T':
            return 1
        if value == 'F':
            return 0
        if '/' in value:
            return float(Fraction(value))
        if '.' in value or value in ('inf', '-inf', 'nan'):
            return float(value)
        return int(value)

    def get_max_depth(self):
        """
        Returns the max depth of the trace
        """
        return trace_get_max_depth(self.rawtrace)

    def get_value(self, net, depth):
        """
        Retrieval of a value from the trace for a net at a depth
        """
        size = trace_prepare_value_for_net(self.ctx, self.rawtrace, net, depth)
        value = ''
        for i in range(size):
            value += value_at(i)
        return value

    def set_value(self, net, depth, value):
        """
        Sets a value for a net at a certain depth
        """
        if value == 'true':
            value = 'T'
        elif value == 'false':
            value = 'F'
        trace_set_value(self.ctx, self.rawtrace, net, depth, value)

    def get_as_net_dictionary(self, net2name=None):
        """
        Return the trace as a dictionary

        net -> [value@0, value@1, ...]
        """
        watched_nets = [trace_get_watched_net(self.rawtrace, i)\
                       for i in range(trace_get_watched_nets_number(self.rawtrace))]
        if net2name is None:
            return {net : list(self._get_as_steps(net)) for net in watched_nets}
        return {net2name[net] : list(self._get_as_steps(net)) for net in watched_nets}

    def get_as_depth_dictionary(self):
        """
        Return the trace as a dictionary

        depth -> [valuenet1@depth, valuenet2@depth, ...]
        """
        return {depth : list(self._get_values_at_depth(depth))\
                for depth in range(trace_get_max_depth(self.rawtrace))}

    def get_as_dataframe(self, net2name):
        """
        Return the trace as a pandas dataframe

                  0       1       2    ...
        name1  value@0 value@1 value@2 ...
        name2  value@0 value@1 value@2 ...
        ...
        """
        matrix = []
        indexes = []
        for net, values in self.get_as_net_dictionary().items():
            indexes.append(net2name[net])
            matrix.append(values)
        return DataFrame(matrix, index=indexes)

    def set_from_dataframe(self, dataframe, inputname2net):
        """
        Return a trace from a pandas dataframe. Only input values
        are considered in filling up the trace
        """
        max_depth = 0
        row = 0
        for name in dataframe.index:
            if name in inputname2net:
                net = inputname2net[name]
                depth = 0
                for value in dataframe.values[row]:
                    self.set_value(net, depth, str(value))
                    if depth > max_depth:
                        max_depth = depth
                    depth += 1
            row += 1
        return max_depth

    def _get_as_steps(self, net):
        max_depth = trace_get_max_depth(self.rawtrace)
        return (self.get_value(net, depth) for depth in range(0, max_depth + 1))

    def _get_values_at_depth(self, depth):
        watched_nets = [trace_get_watched_net(self.rawtrace, i)\
                       for i in range(trace_get_watched_nets_number(self.rawtrace))]
        return (self.get_value(net, depth) for net in watched_nets)
