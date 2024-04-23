import unittest
from unittest.mock import patch
from io import BytesIO
from http.client import HTTPConnection
from sng_exporter import PrometheusRequestHandler, HttpServer, main
import threading
import socket
from time import sleep

class TestPrometheusServer(unittest.TestCase):

    def test_command_line_arguments(self):
        args = ['--listen-address', '127.0.0.1:9577', '--socket-path', '/var/lib/syslog-ng/syslog-ng.ctl', '--stats-with-legacy']
        with patch('sys.argv', ['sng_exporter.py'] + args):
            server_thread = threading.Thread(target=main)
            server_thread.start()
            sleep(1)
            fake_client = socket.socket()
            fake_client.settimeout(1)
            fake_client.connect(('127.0.0.1', 9577))
            fake_client.close()
            print('we are here')
            server_thread.join()



if __name__ == '__main__':
    unittest.main()
