import intrepid
import re
import unittest
from intrepid import PREFIX

CTX_NAME = 'default'

class NetsTestCase(unittest.TestCase):

    def setUp(self):
        self.names = {}
        self.app = intrepid.create_app()
        self.client = self.app.test_client()
        response = self.client.post(PREFIX + 'contexts/create', json={'name': CTX_NAME})
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': CTX_NAME}, response.get_json())
        response = self.client.post(PREFIX + 'inputs/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'type': 'bool'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': '__i0'}, response.get_json())
        self.names['a_boolean'] = '__i0'
        response = self.client.post(PREFIX + 'inputs/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'type': 'bool'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': '__i1'}, response.get_json())
        self.names['b_boolean'] = '__i1'
        response = self.client.post(PREFIX + 'inputs/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'type': 'bool'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': '__i2'}, response.get_json())
        self.names['c_boolean'] = '__i2'
        response = self.client.post(PREFIX + 'inputs/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'type': 'int8'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': '__i3'}, response.get_json())
        self.names['a_int8'] = '__i3'
        response = self.client.post(PREFIX + 'inputs/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'type': 'int8'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': '__i4'}, response.get_json())
        self.names['b_int8'] = '__i4'


    def tearDown(self):
        intrepid.destroy_app()

    def create_bool_constant(self, const, net):
        response = self.client.post(PREFIX + 'nets/{}'.format(const), \
                                    json={ 'context': CTX_NAME })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': net}, response.get_json())

    def create_unary_gate(self, gate, typ):
        response = self.client.post(PREFIX + 'nets/{}/create'.format(gate), \
                                    json={
                                      'context': CTX_NAME,
                                      'x': self.names['a_' + typ]
                                    })
        self.assertEqual(201, response.status_code)

    def create_binary_gate(self, gate, typ):
        response = self.client.post(PREFIX + 'nets/{}/create'.format(gate), \
                                    json={
                                      'context': CTX_NAME,
                                      'x': self.names['a_' + typ],
                                      'y': self.names['b_' + typ]
                                    })
        self.assertEqual(201, response.status_code)

    def test_nets(self):
        response = self.client.get(PREFIX + 'nets?context={}'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'nets': ['__i0',
                                   '__i1',
                                   '__i2',
                                   '__i3',
                                   '__i4']}, response.get_json())

    def test_create_true(self):
        self.create_bool_constant('true', '__n1')

    def test_create_false(self):
        self.create_bool_constant('false', '__n2')

    def test_create_number(self):
        response = self.client.post(PREFIX + 'nets/numbers/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'value': '42',
                                      'type': 'int8'
                                    })
        self.assertEqual(201, response.status_code)
        # The generated name embeds a z3 ast id, which shifts between z3
        # versions, so only its shape is asserted.
        self.assertRegex(response.get_json()['result'], r'^__n\d+$')

    def test_create_unary_bool_gate(self):
        self.create_unary_gate('nots', 'boolean')

    def test_create_unary_int8_gate(self):
        self.create_unary_gate('minuses', 'int8')

    def test_create_binary_bool_gate(self):
        for gate in ['ands', 'ors', 'xors', 'iffs', 'implieses']:
            self.create_binary_gate(gate, 'boolean')

    def test_create_binary_int8_gate(self):
        for gate in ['adds', 'muls', 'divs', 'subs', 'mods',
                     'eqs', 'leqs', 'geqs', 'lts', 'gts', 'neqs']:
            self.create_binary_gate(gate, 'int8')

    def test_create_ite(self):
        response = self.client.post(PREFIX + 'nets/ites/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'x': self.names['a_boolean'],
                                      'y': self.names['a_int8'],
                                      'z': self.names['b_int8']
                                    })
        self.assertEqual(201, response.status_code)
        # The generated name embeds a z3 ast id, which shifts between z3
        # versions, so only its shape is asserted.
        self.assertRegex(response.get_json()['result'], r'^__n\d+$')

    def test_create_cast(self):
        for cast in ['int8', 'int16', 'int32', 'int64',
                     'uint8', 'uint16', 'uint32', 'uint64']:
            response = self.client.post(PREFIX + 'nets/casts/create', \
                                        json={
                                          'context': CTX_NAME,
                                          'x': self.names['a_int8'],
                                          'type': cast
                                        })
            self.assertEqual(201, response.status_code)

if __name__ == '__main__':
    unittest.main()
