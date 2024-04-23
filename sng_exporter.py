import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

# TODO socket path, server port, 'STATS PROMETHEUS WITH_LEGACY\n' paraméterezhetően


class PrometheusRequestHandler(BaseHTTPRequestHandler):
    data = None

    def handle(self):
        # print("Run before request")
        self.data = fetch_syslog_stats()
        BaseHTTPRequestHandler.handle(self)

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(self.data)


def run_server():
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, PrometheusRequestHandler)
    print('Starting server...')
    httpd.serve_forever()


def fetch_syslog_stats():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    socket_path = '/var/lib/syslog-ng/syslog-ng.ctl'
    print("Fetching syslog-ng stats")
    try:
        sock.connect(socket_path)
        # print(f"Successfully connected to {socket}")
    except socket.error:
        print(socket.error)
        sys.exit(1)
    try:
        message = 'STATS PROMETHEUS WITH_LEGACY\n'
        sock.send(message.encode())

        response = b''
        while True:
            chunk = sock.recv(1024)
            # breakpoint()
            response += chunk
            if not chunk or b'.\n' in chunk:
                break

        print("Received:", response.decode())
        return response.decode().strip()[:-1].encode()

    finally:
        print('closing socket')
        sock.close()


def main():
    run_server()


if __name__ == "__main__":
    main()
