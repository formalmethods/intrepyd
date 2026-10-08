Module intrepyd.trace
=====================
This module implements the class for traces

Classes
-------

`Trace(ctx, rawtrace=None)`
:   A trace generated from an Engine, or manually built for use in simulation

    ### Static methods

    `get_numeric_value(value)`
    :   Converts a string value (including true, false) into a corresponding float or integer.
        Reals that are not finite decimals come as fractions, n/d, and floats can be inf,
        -inf and nan.

    ### Methods

    `get_as_dataframe(self, net2name)`
    :   Return the trace as a pandas dataframe
        
                  0       1       2    ...
        name1  value@0 value@1 value@2 ...
        name2  value@0 value@1 value@2 ...
        ...

    `get_as_depth_dictionary(self)`
    :   Return the trace as a dictionary
        
        depth -> [valuenet1@depth, valuenet2@depth, ...]

    `get_as_net_dictionary(self, net2name=None)`
    :   Return the trace as a dictionary
        
        net -> [value@0, value@1, ...]

    `get_max_depth(self)`
    :   Returns the max depth of the trace

    `get_value(self, net, depth)`
    :   Retrieval of a value from the trace for a net at a depth

    `set_from_dataframe(self, dataframe, inputname2net)`
    :   Return a trace from a pandas dataframe. Only input values
        are considered in filling up the trace

    `set_value(self, net, depth, value)`
    :   Sets a value for a net at a certain depth