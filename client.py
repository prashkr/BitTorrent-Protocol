import socket
import sys

messages = [ 'My ',
             'Name ',
             'is Anthony',
             ]

host = sys.argv[1]
port = int(sys.argv[2])
server_address = (host, port)
msg = "REQUEST_PEERS:tracker:"+host+":"+str(port)+":done"

# Create a TCP/IP socket
'''socks = [ socket.socket(socket.AF_INET, socket.SOCK_STREAM),
          socket.socket(socket.AF_INET, socket.SOCK_STREAM),
          ]'''
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Connect the socket to the port where the server is listening
print >>sys.stderr, 'connecting to %s port %s' % server_address
s.connect(server_address)

print >>sys.stderr,'%s: sending "%s"' % (s.getsockname(), msg)
s.send(msg)
data = s.recv(1024)
print >>sys.stderr,'%s: received "%s"' % (s.getsockname(), data)

if not data:
  print >>sys.stderr, 'closing socket', s.getsockname()
  s.close()

'''
for message in messages:

    # Send messages on both sockets
    for s in socks:
        print >>sys.stderr,'%s: sending "%s"' % (s.getsockname(), message)
        s.send(message)

    # Read responses on both sockets
    for s in socks:
        data = s.recv(1024)
        print >>sys.stderr,'%s: received "%s"' % (s.getsockname(), data)
        if not data:
            print >>sys.stderr, 'closing socket', s.getsockname()
            s.close()'''