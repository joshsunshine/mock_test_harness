import unittest
from flask import Flask, request
import th_endpoints
from th_endpoints import shutdown_server
from time import sleep


class EndpointTestCase(unittest.TestCase):

    def setUp(self):
        self.app = th_endpoints.app.test_client()

    def test_status(self):
        rv = self.app.post('/action/status')
        print(rv.data)
        assert b'Status' in rv.data

    def test_ready(self):
        rv = self.app.post('/ready')
        print(rv.data)
        sleep(1)
        rv = self.app.post('action/done')
        print(rv.data)
        assert b'10' in rv.data

if __name__ == '__main__':
    unittest.main()
