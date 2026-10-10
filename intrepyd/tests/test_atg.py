import unittest
import intrepyd
from intrepyd.atg import mcdc
from intrepyd.circuit import Circuit


class TestAtg(unittest.TestCase):
    def test_atg_01(self):
        ctx = intrepyd.Context()
        decisions = {'O': ['A', 'B']}
        tables, indpairs, decision2unreachable = mcdc.compute_mcdc(ctx, CircAnd, decisions, max_depth=10)
        decision2dataframe = mcdc.get_tables_as_dataframe(tables)
        self.assertEqual(3, len(decision2dataframe['O']))
        self.assertEqual(2, len(indpairs['O']))
        self.assertEqual(0, len(decision2unreachable['O']))

    def test_atg_02(self):
        ctx = intrepyd.Context()
        decisions = {'Out': ['In1', 'In2', 'In3', 'In4', 'In5', 'In6']}
        tables, indpairs, decision2unreachable = mcdc.compute_mcdc(ctx, CircFmics2021, decisions, max_depth=10)
        decision2dataframe = intrepyd.atg.mcdc.get_tables_as_dataframe(tables)
        self.assertEqual(8, len(decision2dataframe['Out']))
        self.assertEqual(6, len(indpairs['Out']))
        self.assertEqual(0, len(decision2unreachable['Out']))


class CircAnd(Circuit):
    """O = A and B, with A and B as conditions and O as the decision."""

    def _mk_inputs(self):
        bt = self.context.mk_boolean_type()
        self.inputs['A'] = self.context.mk_input('A', bt)
        self.inputs['B'] = self.context.mk_input('B', bt)
        self.nets.update(self.inputs)

    def _mk_naked_circuit_impl(self, inputs):
        out = self.context.mk_and(inputs['A'], inputs['B'])
        self.nets['O'] = out
        return {'O': out}


class CircFmics2021(Circuit):
    """Out = (In1|In2) & (In3|In4) | (In5 & In6): six conditions, one decision."""

    def _mk_inputs(self):
        bt = self.context.mk_boolean_type()
        for i in range(1, 7):
            name = 'In{}'.format(i)
            self.inputs[name] = self.context.mk_input(name, bt)
        self.nets.update(self.inputs)

    def _mk_naked_circuit_impl(self, inputs):
        ctx = self.context
        self.nets['gate1'] = ctx.mk_or(inputs['In1'], inputs['In2'])
        self.nets['gate2'] = ctx.mk_or(inputs['In3'], inputs['In4'])
        self.nets['gate3'] = ctx.mk_and(inputs['In5'], inputs['In6'])
        self.nets['gate4'] = ctx.mk_and(self.nets['gate1'], self.nets['gate2'])
        self.nets['gate5'] = ctx.mk_or(self.nets['gate3'], self.nets['gate4'])
        self.nets['Out'] = self.nets['gate5']
        return {'Out': self.nets['Out']}


if __name__ == '__main__':
    unittest.main()
