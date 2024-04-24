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
        logging.debug("Fetching syslog-ng stats")
        sock = self.create_socket_connection(socket_path)
        try:
            message = stats_with_legacy
            sock.send(message.encode())

            response = b''
            while True:
                chunk = sock.recv(1024)
                response += chunk
                if not chunk or b'.\n' in chunk:
                    break

            logging.debug(f"Received:\n{response.decode()}")
            return response.decode().strip()[:-1].encode()

        finally:
            logging.debug('closing socket')
            sock.close()

    @classmethod
    def create_socket_connection(cls, socket_path, check_only=False):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        try:
            sock.connect(socket_path)
        except socket.error as e:
            logging.error(f"Socket connection error: {e}: {socket_path}")
            sys.exit(1)

        if check_only:
            sock.close()
            logging.debug("Successfully connected to syslog-ng-ctl socket")
            return

        return sock


class HttpServer:
    def __init__(self, listen_address, socket_path, stats_type):
        PrometheusRequestHandler.socket_path = socket_path
        PrometheusRequestHandler.stats_with_legacy = stats_type
        self.server = HTTPServer((listen_address.split(":")[0], int(listen_address.split(":")[1])),
                                 PrometheusRequestHandler)
        try:
            self.server.serve_forever()
            logging.info("Service successfully started")
        except KeyboardInterrupt:
            logging.info("Service stopped")
            self.server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="Command line script to export syslog-ng stats to Prometheus.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--listen-address", dest="listen_address", help="Service listen address", default=":9577")
    parser.add_argument("--socket-path", dest="socket_path", help="Path to the syslog-ng-ctl socket",
                        default='/var/lib/syslog-ng/syslog-ng.ctl')
    parser.add_argument("--stats-with-legacy", dest="stats_with_legacy", action="store_true",
                        help="Enable syslog-ng log processing statistics")
    parser.add_argument("--log-level", dest="log_level", help="Only log messages with the given severity or above. "
                                                              "One of: [debug, info, error]", default="info")
    args = parser.parse_args()

    stats = 'STATS PROMETHEUS\n'
    if args.stats_with_legacy:
        stats = 'STATS PROMETHEUS WITH_LEGACY\n'

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log_level)
    logging.basicConfig(level=numeric_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                        )
    logging.info("Starting Prometheus syslog-ng exporter...")
    logging.debug(f"Socket Path: {args.socket_path}")
    logging.debug(f"Listen address: {args.listen_address}")
    logging.debug(f"Stats with Legacy: {stats}")

    logging.debug("Checking syslog-ng-ctl socket")
    PrometheusRequestHandler.create_socket_connection(args.socket_path, check_only=True)
    server = HttpServer(args.listen_address, args.socket_path, stats)


if __name__ == "__main__":
    main()
