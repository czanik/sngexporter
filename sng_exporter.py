import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class PrometheusRequestHandler(BaseHTTPRequestHandler):
    data = None

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()                        # Your metrics here in Prometheus exposition format            response_body = b"my_custom_metric 42"                        self.wfile.write(response_body)        else:
            self.wfile.write(self.data)

def run_server(senddata):
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, PrometheusRequestHandler)
    PrometheusRequestHandler.data = senddata
    print('Starting server...')
    httpd.serve_forever()


print("syslog-ng prometheus exporter")

# Create a UDS socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)


socket_path = '/var/lib/syslog-ng/syslog-ng.ctl'
print(sys.stderr, 'connecting to %s' % socket_path)
try:
    sock.connect(socket_path)
    print(f"Successfully connected to {socket}")
except socket.error:
    print(socket.error)
    sys.exit(1)

try:
    # Send data
    message = 'STATS PROMETHEUS WITH_LEGACY\n'
    sock.send(message.encode())

    # Receive data
    response = b''
    while True:
        chunk = sock.recv(1024)
        if not chunk or b'.\n' in chunk:
            break
        response += chunk
    print("Received:", response.decode())
    run_server(response)

finally:
    print('closing socket')
    sock.close()
