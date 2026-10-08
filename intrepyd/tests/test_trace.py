import math
import intrepyd
import intrepyd.trace
import unittest

class TestTrace(unittest.TestCase):

    def test_trace_01(self):
        ctx = intrepyd.Context()
        tr = ctx.mk_trace()
        i0 = ctx.mk_input('i0', ctx.mk_boolean_type())
        i1 = ctx.mk_input('i1', ctx.mk_boolean_type())
        i2 = ctx.mk_input('i2', ctx.mk_int8_type())
        i3 = ctx.mk_input('i3', ctx.mk_int16_type())
        i4 = ctx.mk_input('i4', ctx.mk_int32_type())
        i5 = ctx.mk_input('i5', ctx.mk_uint8_type())
        i6 = ctx.mk_input('i6', ctx.mk_uint16_type())
        i7 = ctx.mk_input('i7', ctx.mk_uint32_type())
        i8 = ctx.mk_input('i8', ctx.mk_real_type())
        tr.set_value(i0, 0, 'F')
        tr.set_value(i1, 0, 'T')
        tr.set_value(i2, 0, '1')
        tr.set_value(i3, 0, '2')
        tr.set_value(i4, 0, '3')
        tr.set_value(i5, 0, '4')
        tr.set_value(i6, 0, '5')
        tr.set_value(i7, 0, '6')
        tr.set_value(i8, 0, '7.0')
        self.assertEqual('F', tr.get_value(i0, 0))
        self.assertEqual('T', tr.get_value(i1, 0))
        self.assertEqual('1', tr.get_value(i2, 0))
        self.assertEqual('2', tr.get_value(i3, 0))
        self.assertEqual('3', tr.get_value(i4, 0))
        self.assertEqual('4', tr.get_value(i5, 0))
        self.assertEqual('5', tr.get_value(i6, 0))
        self.assertEqual('6', tr.get_value(i7, 0))
        self.assertEqual('7.0', tr.get_value(i8, 0))
        nv = intrepyd.trace.Trace.get_numeric_value
        self.assertEqual(0, nv(tr.get_value(i0, 0)))
        self.assertEqual(1, nv(tr.get_value(i1, 0)))
        self.assertEqual(1, nv(tr.get_value(i2, 0)))
        self.assertEqual(2, nv(tr.get_value(i3, 0)))
        self.assertEqual(3, nv(tr.get_value(i4, 0)))
        self.assertEqual(4, nv(tr.get_value(i5, 0)))
        self.assertEqual(5, nv(tr.get_value(i6, 0)))
        self.assertEqual(6, nv(tr.get_value(i7, 0)))
        self.assertEqual(7.0, nv(tr.get_value(i8, 0)))
        self.assertEqual(-0.25, nv('-1/4'))
        self.assertAlmostEqual(1 / 3, nv('1/3'))
        self.assertEqual(float('-inf'), nv('-inf'))
        self.assertTrue(math.isnan(nv('nan')))
        self.assertEqual('?', nv('?'))
        df = tr.get_as_dataframe(ctx.net2name)
        self.assertEqual('F', df.iloc[0, 0])
        dd = tr.get_as_depth_dictionary()
        nd = tr.get_as_net_dictionary(ctx.net2name)

if __name__ == '__main__':
    unittest.main()
