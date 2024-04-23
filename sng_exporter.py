import argparse
import logging
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class PrometheusRequestHandler(BaseHTTPRequestHandler):
    socket_path = None
    stats_with_legacy = None
    data = None

    def handle(self):
        self.data = self.fetch_syslog_stats(self.socket_path, self.stats_with_legacy)
        BaseHTTPRequestHandler.handle(self)

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(self.data)

    def fetch_syslog_stats(self, socket_path, stats_with_legacy):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        logging.info("Fetching syslog-ng stats")
        try:
            sock.connect(socket_path)
        except socket.error as e:
            logging.error(f"Socket connection error: {e}")
            sys.exit(1)
        try:
            message = stats_with_legacy
            sock.send(message.encode())

            response = b''
            while True:
                chunk = sock.recv(1024)
                response += chunk
                if not chunk or b'.\n' in chunk:
                    break

            logging.info("Received:", response.decode())
            return response.decode().strip()[:-1].encode()

        finally:
            logging.info('closing socket')
            sock.close()


class HttpServer:
    def __init__(self, listen_address, socket_path, stats_type):
        PrometheusRequestHandler.socket_path = socket_path
        PrometheusRequestHandler.stats_with_legacy = stats_type
        self.server = HTTPServer((listen_address.split(":")[0], int(listen_address.split(":")[1])), PrometheusRequestHandler)
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print('Server stopped.')
            self.server.close()


def main():
    parser = argparse.ArgumentParser(
        description="Command line script to export syslog-ng stats to Prometheus.")
    parser.add_argument("--listen-address", dest="listen_address", help="Listen address", default=':9577')
    parser.add_argument("--socket-path", dest="socket_path", help="Path to the syslog-ng-ctl socket", default='/var/lib/syslog-ng/syslog-ng.ctl')
    parser.add_argument("--stats-with-legacy", dest="stats_with_legacy", action="store_true",
                        help="Enable stats with legacy")
    args = parser.parse_args()

    stats = 'STATS PROMETHEUS\n'
    if args.stats_with_legacy:
        stats = 'STATS PROMETHEUS WITH_LEGACY\n'

    logging.info("Socket Path:", args.socket_path)
    logging.info("Listen address:", args.listen_address)
    logging.info("Stats with Legacy:", stats)
    server = HttpServer(args.listen_address, args.socket_path, stats)


if __name__ == "__main__":
    main()
