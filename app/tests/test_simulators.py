import intrepid
import unittest
from intrepid import PREFIX

CTX_NAME = 'default'

class SimulatorsTestCase(unittest.TestCase):

    def setUp(self):
        self.names = {}
        self.app = intrepid.create_app()
        self.client = self.app.test_client()
        response = self.client.post(PREFIX + 'contexts/create', json={'name': CTX_NAME})
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': CTX_NAME}, response.get_json())
        response = self.client.post(PREFIX + 'nets/true', \
                                    json={ 'context': CTX_NAME })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': '__n1'}, response.get_json())
        self.create_latch('__l0')
        self.create_latch('__l1')
        response = self.client.post(PREFIX + 'nets/ands/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'x': '__l0',
                                      'y': '__l1'
                                    })
        self.assertEqual(201, response.status_code)
        # Generated names embed z3 ast ids, which shift between z3 versions:
        # remember what the service returned rather than hardcoding it.
        self.and_net = response.get_json()['result']

    def tearDown(self):
        intrepid.destroy_app()

    def create_latch(self, name):
        response = self.client.post(PREFIX + 'latches/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'type': 'bool'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': name}, response.get_json())
        response = self.client.put(PREFIX + 'latches/initnext', \
                                    json={
                                      'context': CTX_NAME,
                                      'latch': name,
                                      'init': '__n1',
                                      'next': '__n1'
                                    })
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 'ok'}, response.get_json())

    def test_simulator(self):
        response = self.client.post(PREFIX + 'simulators/create', \
                                    json={
                                      'context': CTX_NAME
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': 's0'}, response.get_json())
        response = self.client.post(PREFIX + 'traces/create', \
                                    json={
                                      'context': CTX_NAME
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': 't0'}, response.get_json())
        response = self.client.put(PREFIX + 'simulators/watch', \
                                    json={
                                      'context': CTX_NAME,
                                      'simulator': 's0',
                                      'net': self.and_net
                                    })
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 'ok'}, response.get_json())
        response = self.client.put(PREFIX + 'simulators/simulate', \
                                    json={
                                      'context': CTX_NAME,
                                      'simulator': 's0',
                                      'trace': 't0',
                                      'depth': 0
                                    })
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 'ok'}, response.get_json())
        response = self.client.get(PREFIX + 'traces/value?context={}&trace=t0&depth=0&net={}'.format(CTX_NAME, self.and_net))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 'T'}, response.get_json())

if __name__ == '__main__':
    unittest.main()
