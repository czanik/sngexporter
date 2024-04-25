import unittest
from unittest.mock import patch
from io import BytesIO
from http.client import HTTPConnection
from sng_exporter import PrometheusRequestHandler, SngExporterServer, main
import multiprocessing
import socket
from time import sleep
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO as IO

class TestPrometheusServer(unittest.TestCase):

    def test_request(self):
        args = ['--listen-address', 'localhost:9577', '--socket-path', '/var/lib/syslog-ng/syslog-ng.ctl', '--stats-with-legacy']
        with patch('sys.argv', ['sng_exporter.py'] + args):
            server_proc = multiprocessing.Process(target=main, args=())
            server_proc.start()
            # Terminate the process
            sleep(1)

            r = requests.get('http://localhost:9577/metrics')
            self.assertEqual(r.status_code, 200)
            self.assertIsNotNone(r.content)
            self.assertNotEqual(r.content[-1], '.')
            server_proc.terminate()  # sends a SIGTERMimport socket

    def test_client(self):
        args = ['--listen-address', 'localhost:9577', '--socket-path', '/var/lib/syslog-ng/syslog-ng.ctl', '--stats-with-legacy']
        with patch('sys.argv', ['sng_exporter.py'] + args):
            server_proc = multiprocessing.Process(target=main, args=())
            server_proc.start()
            # Terminate the process
            sleep(1)

            fake_client = socket.socket()
            fake_client.settimeout(1)
            fake_client.connect(('localhost', 9577))
            fake_client.close()
            print(fake_client)
            server_proc.terminate()  # sends a SIGTERMimport socket

    def test_mock_server(self):
        """Test the custom HTTP request handler by mocking a server"""
        class MockRequest(object):
            def makefile(self, *args, **kwargs):
                return IO(b"GET /")

        class MockServer(object):
            def __init__(self, ip_port, Handler):
                handler = Handler(MockRequest(), ip_port, self)

        # The GET request will be sent here
        # and any exceptions will be propagated through.
        PrometheusRequestHandler.socket_path = '/var/lib/syslog-ng/syslog-ng.ctl'
        PrometheusRequestHandler.stats_with_legacy = 'STATS PROMETHEUS WITH_LEGACY\n'
        server = MockServer(('0.0.0.0', 8888), PrometheusRequestHandler)

if __name__ == '__main__':
    unittest.main()
