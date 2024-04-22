import socket
import sys

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

finally:
    print('closing socket')
    sock.close()
