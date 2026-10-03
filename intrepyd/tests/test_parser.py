from intrepyd.parser import Parser
import unittest
import tempfile
import io
import os

class TestParser(unittest.TestCase):
    def assertNets(self, expected_names, ctx):
        """
        Checks which nets a parse produced.

        The values in ctx.nets are z3 ast ids: they are an internal detail of
        the solver and shift whenever z3 changes how many terms it creates up
        front, so only the names are asserted here.
        """
        self.assertEqual(sorted(expected_names), sorted(ctx.nets.keys()))

    def test_it_parses_inputs(self):
        stream = io.StringIO(
            """
            i1 = input bool
            i2 = input bool
            a1 = and i1 i2
            """
        )
        parser = Parser()
        ctx = parser.parse_stream(stream)
        self.assertNets(['__n1', '__n2', 'a1', 'false', 'i1', 'i2', 'true'], ctx)

    def test_it_parses_latches(self):
        stream = io.StringIO(
            """
            l1 = latch bool
            set_latch_init_next l1 true false
            l2 = latch bool
            set_latch_init_next l2 false true
            o1 = or l1 l2
            """
        )
        parser = Parser()
        ctx = parser.parse_stream(stream)
        self.assertNets(['__n1', '__n2', 'false', 'l1', 'l2', 'o1', 'true'], ctx)

    def test_it_parses_numbers(self):
        stream = io.StringIO(
            """
            n0 = number 0 int8
            n1 = number 1 int8
            a1 = add n0 n1
            """
        )
        parser = Parser()
        ctx = parser.parse_stream(stream)
        self.assertNets(['__n1', '__n2', 'a1', 'false', 'n0', 'n1', 'true'], ctx)

    def test_it_parses_comments(self):
        stream = io.StringIO(
            """
            # This is a comment
            l1 = latch bool
            set_latch_init_next l1 true false
            """
        )
        parser = Parser()
        ctx = parser.parse_stream(stream)
        self.assertNets(['__n1', '__n2', 'false', 'l1', 'true'], ctx)

    def test_it_parses_types(self):
        stream = io.StringIO(
            """
            i1 = input bool
            i2 = input int8
            i3 = input int16
            i4 = input int32
            i5 = input uint8
            i6 = input uint16
            i7 = input uint32
            i8 = input float16
            i9 = input float32
            i10 = input float64
            i11 = input real
            i12 = input int
            """
        )
        parser = Parser()
        ctx = parser.parse_stream(stream)
        self.assertNets([
            '__n1', '__n2', 'false', 'i1', 'i10', 'i11', 'i12', 'i2', 'i3', 'i4', 'i5', 'i6',
            'i7', 'i8', 'i9', 'true'
        ], ctx)

    def test_it_parses_files(self):
        with tempfile.TemporaryDirectory() as dirname:
            filepath = os.path.join(dirname, 'temp.itd')
            f = open(filepath, 'wt')
            f.write(
                """
                i1 = input bool
                n1 = not i1
                """
            )
            f.close()
            parser = Parser()
            ctx = parser.parse_file(filepath)
            self.assertNets(['__n1', '__n2', 'false', 'i1', 'n1', 'true'], ctx)

    def test_it_parses_and_creates(self):
        stream = io.StringIO(
            """
            i1 = input bool
            i2 = input bool
            """
        )
        parser = Parser()
        ctx = parser.parse_stream(stream)
        self.assertNets(['__n1', '__n2', 'false', 'i1', 'i2', 'true'], ctx)
        ctx.mk_and(ctx.nets['i1'], ctx.nets['i2'], 'a1')
        self.assertNets(['__n1', '__n2', 'a1', 'false', 'i1', 'i2', 'true'], ctx)

    def test_it_parses_relations(self):
        stream = io.StringIO(
            """
            n1 = number 0 int8
            i1 = input int8
            e1 = eq n1 i1
            """
        )
        parser = Parser()
        ctx = parser.parse_stream(stream)
        self.assertNets(['__n1', '__n2', 'e1', 'false', 'i1', 'n1', 'true'], ctx)

if __name__ == '__main__':
    unittest.main()
