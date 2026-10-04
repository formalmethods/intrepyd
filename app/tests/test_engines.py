"""
APIs for engines
"""

import intrepid
import unittest
from intrepid import PREFIX

CTX_NAME = 'default'

class EnginesTestCase(unittest.TestCase):

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

    def tearDown(self):
        intrepid.destroy_app()

    def create_bmc(self):
        response = self.client.post(PREFIX + 'engines/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'bmc'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': 'e0'}, response.get_json())

    def create_optimizing_bmc(self):
        response = self.client.post(PREFIX + 'engines/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'optimizing_bmc'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': 'e1'}, response.get_json())

    def create_backward_reach(self):
        response = self.client.post(PREFIX + 'engines/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'backward_reach'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': 'e2'}, response.get_json())

    def create_engines(self):
        self.create_bmc()
        response = self.client.get(PREFIX + 'engines?context={}'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'engines': ['e0']}, response.get_json())
        self.create_optimizing_bmc()
        response = self.client.get(PREFIX + 'engines?context={}'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'engines': ['e0', 'e1']}, response.get_json())
        self.create_backward_reach()
        response = self.client.get(PREFIX + 'engines?context={}'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'engines': ['e0', 'e1', 'e2']}, response.get_json())

    def test_engines(self):
        response = self.client.get(PREFIX + 'engines?context={}'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'engines': []}, response.get_json())

    def test_create_assumptions(self):
        response = self.client.post(PREFIX + 'engines/assumptions/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'net': '__i0'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': 'ok'}, response.get_json())

    def test_create_engines(self):
        self.create_engines()

    def test_set_current_depth(self):
        self.create_engines()
        for eng in ['e0', 'e1']:
            response = self.client.put(PREFIX + 'engines/setcurrentdepth', \
                                        json={
                                          'context': CTX_NAME,
                                          'engine': eng,
                                          'depth': 42
                                        })
            self.assertEqual(200, response.status_code)
            self.assertEqual({'result': 42}, response.get_json())
        response = self.client.put(PREFIX + 'engines/setallowtargetsatanydepth', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'e2'
                                    })
        self.assertEqual(400, response.status_code)

    def test_set_use_induction(self):
        self.create_engines()
        for eng in ['e0', 'e1']:
            response = self.client.put(PREFIX + 'engines/setuseinduction', \
                                        json={
                                          'context': CTX_NAME,
                                          'engine': eng
                                        })
            self.assertEqual(200, response.status_code)
            self.assertEqual({'result': 'ok'}, response.get_json())
        response = self.client.put(PREFIX + 'engines/setallowtargetsatanydepth', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'e2'
                                    })
        self.assertEqual(400, response.status_code)

    def test_set_allow_targets_at_any_depth(self):
        self.create_engines()
        for eng in ['e0', 'e1']:
            response = self.client.put(PREFIX + 'engines/setallowtargetsatanydepth', \
                                        json={
                                          'context': CTX_NAME,
                                          'engine': eng
                                        })
            self.assertEqual(200, response.status_code)
            self.assertEqual({'result': 'ok'}, response.get_json())
        response = self.client.put(PREFIX + 'engines/setallowtargetsatanydepth', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'e2'
                                    })
        self.assertEqual(400, response.status_code)

    def test_add_reach_trace(self):
        self.create_engines()
        #
        # Adding targets
        #
        response = self.client.put(PREFIX + 'engines/addtarget', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'e0',
                                      'net': self.names['a_boolean']
                                    })
        self.assertEqual(200, response.status_code)
        #
        # Reaching targets
        #
        response = self.client.put(PREFIX + 'engines/reachtargets', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'e0'
                                    })
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 'reachable'}, response.get_json())
        #
        # Getting reachable targets
        #
        response = self.client.get(PREFIX + 'engines/lastreachedtargets?context={}&engine=e0'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': [self.names['a_boolean']]}, response.get_json())
        #
        # Getting last trace
        #
        response = self.client.get(PREFIX + 'engines/lasttrace?context={}&engine=e0'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 't0'}, response.get_json())
        #
        # Getting trace depth
        #
        response = self.client.get(PREFIX + 'traces/maxdepth?context={}&trace=t0'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 0}, response.get_json())
        #
        # Getting trace values
        #
        response = self.client.get(PREFIX + 'traces/values?context={}&trace=t0'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': {'__i0': ['T']}}, response.get_json())
        #
        # Getting a trace value
        #
        response = self.client.get(PREFIX + 'traces/value?context={}&trace=t0&depth=0&net=__i0'.format(CTX_NAME))
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 'T'}, response.get_json())

    def test_portfolio(self):
        response = self.client.post(PREFIX + 'engines/create', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'portfolio'
                                    })
        self.assertEqual(201, response.status_code)
        self.assertEqual({'result': 'e0'}, response.get_json())
        response = self.client.put(PREFIX + 'engines/addtarget', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'e0',
                                      'net': self.names['a_boolean']
                                    })
        self.assertEqual(200, response.status_code)
        response = self.client.put(PREFIX + 'engines/reachtargets', \
                                    json={
                                      'context': CTX_NAME,
                                      'engine': 'e0'
                                    })
        self.assertEqual(200, response.status_code)
        self.assertEqual({'result': 'reachable'}, response.get_json())
        response = self.client.get(PREFIX + 'engines/lastreachedtargets?context={}&engine=e0'.format(CTX_NAME))
        self.assertEqual({'result': [self.names['a_boolean']]}, response.get_json())
        response = self.client.get(PREFIX + 'engines/lasttrace?context={}&engine=e0'.format(CTX_NAME))
        self.assertEqual({'result': 't0'}, response.get_json())
        response = self.client.get(PREFIX + 'traces/values?context={}&trace=t0'.format(CTX_NAME))
        self.assertEqual({'result': {'__i0': ['T']}}, response.get_json())

if __name__ == '__main__':
    unittest.main()
