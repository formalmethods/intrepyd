"""
A parser for the Intrepid's language
"""

from intrepyd.context import Context

class ParseError(Exception):
    """
    Encapsulates a parsing error
    """
    def __init__(self, message):
        super().__init__(message)
        self._message = message

    def message(self):
        """
        Retrieves the error message
        """
        return self._message

class Parser:
    """
    A parser for Intrepid's syntax
    """
    def __init__(self):
        self._ctx = Context()
        self._special_ops = set(['set_latch_init_next'])
        self._initialize_parsing_functions()
        self._initialize_types()
        self._ctx.nets['true'] = self._ctx.mk_true()
        self._ctx.nets['false'] = self._ctx.mk_false()

    def _initialize_types(self):
        self._name_to_type = {
          'bool': self._ctx.mk_boolean_type(),
          'int8': self._ctx.mk_int8_type(),
          'int16': self._ctx.mk_int16_type(),
          'int32': self._ctx.mk_int32_type(),
          'int64': self._ctx.mk_int64_type(),
          'uint8': self._ctx.mk_uint8_type(),
          'uint16': self._ctx.mk_uint16_type(),
          'uint32': self._ctx.mk_uint32_type(),
          'uint64': self._ctx.mk_uint64_type(),
          'float16': self._ctx.mk_float16_type(),
          'float32': self._ctx.mk_float32_type(),
          'float64': self._ctx.mk_float64_type(),
          'real': self._ctx.mk_real_type(),
          'int': self._ctx.mk_int_type()
        }

    def _initialize_parsing_functions(self):
        self._op_to_unary_func = {}
        self._op_to_binary_func = {}
        self._op_to_ternary_func = {}
        self._op_to_unary_func['not'] = self._ctx.mk_not
        self._op_to_unary_func['minus'] = self._ctx.mk_minus
        self._op_to_unary_func['to_int8'] = self._ctx.mk_cast_to_int8
        self._op_to_unary_func['to_int16'] = self._ctx.mk_cast_to_int16
        self._op_to_unary_func['to_int32'] = self._ctx.mk_cast_to_int32
        self._op_to_unary_func['to_int64'] = self._ctx.mk_cast_to_int64
        self._op_to_unary_func['to_uint8'] = self._ctx.mk_cast_to_uint8
        self._op_to_unary_func['to_uint16'] = self._ctx.mk_cast_to_uint16
        self._op_to_unary_func['to_uint32'] = self._ctx.mk_cast_to_uint32
        self._op_to_unary_func['to_uint64'] = self._ctx.mk_cast_to_uint64
        self._op_to_binary_func['and'] = self._ctx.mk_and
        self._op_to_binary_func['or'] = self._ctx.mk_or
        self._op_to_binary_func['xor'] = self._ctx.mk_xor
        self._op_to_binary_func['iff'] = self._ctx.mk_iff
        self._op_to_binary_func['implies'] = self._ctx.mk_implies
        self._op_to_binary_func['eq'] = self._ctx.mk_eq
        self._op_to_binary_func['neq'] = self._ctx.mk_neq
        self._op_to_binary_func['leq'] = self._ctx.mk_leq
        self._op_to_binary_func['geq'] = self._ctx.mk_geq
        self._op_to_binary_func['lt'] = self._ctx.mk_lt
        self._op_to_binary_func['gt'] = self._ctx.mk_gt
        self._op_to_binary_func['add'] = self._ctx.mk_add
        self._op_to_binary_func['mul'] = self._ctx.mk_mul
        self._op_to_binary_func['div'] = self._ctx.mk_div
        self._op_to_binary_func['sub'] = self._ctx.mk_sub
        self._op_to_binary_func['mod'] = self._ctx.mk_mod
        self._op_to_ternary_func['ite'] = self._ctx.mk_ite

    def parse_file(self, filepath):
        """
        Parses the file, and returns the context
        """
        with open(filepath, "rt", encoding="utf-8") as file:
            return self.parse_stream(file)

    def parse_stream(self, stream):
        """
        Parses the stream, and returns the context
        """
        return self._parse(stream)

    def _parse(self, file):
        lineno = 1
        line = file.readline()
        while line:
            self._parse_line(line, lineno)
            lineno += 1
            line = file.readline()
        return self._ctx

    def _parse_line(self, line, lineno):
        line = line.strip()
        if len(line) == 0:
            return
        if line[0] == '#':
            return
        tokens = line.split()
        if len(tokens) < 4:
            raise ParseError(f"Parse error at line {lineno}: less than four tokens")
        if len(tokens) > 6:
            raise ParseError(f"Parse error at line {lineno}: more than six tokens")
        if tokens[0] in self._special_ops:
            self._parse_special_op(line, lineno)
            return
        identifier = tokens[0]
        if identifier in self._ctx.nets:
            raise ParseError(f'Parse error at line {lineno}: identifier {identifier} already used')
        if tokens[1] != '=':
            raise ParseError(f'Parse error at line {lineno}: expected =, found {tokens[1]}')
        operator = tokens[2]
        x = None
        y = None
        z = None
        net = None
        if len(tokens) >= 4:
            x = tokens[3]
        if operator in ('latch', 'input'):
            if len(tokens) != 4:
                raise ParseError(f'Parse error at line {lineno}: unexpected token {tokens[4]}')
            if x not in self._name_to_type:
                raise ParseError(f'Parse error at line {lineno}: unrecognized type {x}')
            x = self._name_to_type[x]
            if operator == 'latch':
                net = self._ctx.mk_latch(identifier, x)
            if operator == 'input':
                net = self._ctx.mk_input(identifier, x)
            assert net is not None
            assert self._ctx.nets[identifier] == net
            return
        if len(tokens) >= 5:
            y = tokens[4]
        if operator == 'number':
            if len(tokens) != 5:
                raise ParseError(f'Parse error at line {lineno}: unexpected token {tokens[5]}')
            if y not in self._name_to_type:
                raise ParseError(f'Parse error at line {lineno}: unrecognized type {x}')
            y = self._name_to_type[y]
            net = self._ctx.mk_number(x, y, identifier)
            assert net is not None
            assert self._ctx.nets[identifier] == net
            return
        if len(tokens) >= 4:
            if x not in self._ctx.nets:
                raise ParseError(f'Parse error at line {lineno}: identifier {x} not found')
            x = self._ctx.nets[x]
        if len(tokens) >= 5:
            if y not in self._ctx.nets:
                raise ParseError(f'Parse error at line {lineno}: identifier {y} not found')
            y = self._ctx.nets[y]
        if len(tokens) >= 6:
            z = tokens[5]
            if z not in self._ctx.nets:
                raise ParseError(f'Parse error at line {lineno}: identifier {z} not found')
            z = self._ctx.nets[z]
        # Unary operators
        if len(tokens) == 4:
            assert x is not None
            if operator not in self._op_to_unary_func:
                raise ParseError(f'Parse error at line {lineno}: operator {operator} not found')
            net = self._op_to_unary_func[operator](x, identifier)
        # Binary operators
        if len(tokens) == 5:
            assert x is not None
            assert y is not None
            if operator not in self._op_to_binary_func:
                raise ParseError(f'Parse error at line {lineno}: operator {operator} not found')
            net = self._op_to_binary_func[operator](x, y, identifier)
        # Ternary operators
        if len(tokens) == 6:
            assert x is not None
            assert y is not None
            assert z is not None
            if operator not in self._op_to_ternary_func:
                raise ParseError(f'Parse error at line {lineno}: operator {operator} not found')
            net = self._op_to_ternary_func[operator](x, y, z, identifier)
        assert net is not None
        assert self._ctx.nets[identifier] == net

    def _parse_special_op(self, line, lineno):
        tokens = line.split()
        operator = tokens[0]
        if operator == 'set_latch_init_next':
            lat = tokens[1]
            ini = tokens[2]
            nex = tokens[3]
            if lat not in self._ctx.nets:
                raise ParseError(f'Parse error at line {lineno}: identifier {lat} not found')
            if ini not in self._ctx.nets:
                raise ParseError(f'Parse error at line {lineno}: identifier {ini} not found')
            if nex not in self._ctx.nets:
                raise ParseError(f'Parse error at line {lineno}: identifier {nex} not found')
            lat = self._ctx.nets[lat]
            ini = self._ctx.nets[ini]
            nex = self._ctx.nets[nex]
            self._ctx.set_latch_init_next(lat, ini, nex)
