import Queue
import select
import socket
import sys

def processMsg(inputMsg):
    flag = True
    peerListReply = "TRACKER_RESPONSE-"
    inputMsg = inputMsg.strip('\n')
    inputMsg = inputMsg.strip(' ')
    inputs = inputMsg.split('-')
    if inputs[0] == 'REQUEST_PEERS':
        msgBody = inputs[1].split(',')
        # filename = msgBody[1].split(':')[1]
        filename = "tracker.txt"
        host, port = msgBody[0].split(':')
        with open(filename, 'rw') as f:
            for line in f:
                line = line.strip('\n')
                print line
                if flag:
                    flag = False
                    peerListReply = peerListReply + line
                else:
                    peerListReply = peerListReply + ',' + line

                # createFile(filename,host+':'+port)
    return peerListReply


def createFile(fileName, peer):
    f = open(fileName, 'a')
    f.write(peer)
    f.close()


if __name__ == '__main__':

    host = sys.argv[1]
    port = int(sys.argv[2])
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(0)
    # Bind the socket to the port
    server_address = (host, port)
    print >> sys.stderr, 'starting up on %s port %s' % server_address
    server.bind(server_address)
    # Listen for incoming connections
    server.listen(5)
    # Sockets from which we expect to read
    inputs = [server]

    # Sockets to which we expect to write
    outputs = []
    # Outgoing message queues (socket:Queue)
    message_queues = {}
    while inputs:

        # Wait for at least one of the sockets to be ready for processing
        print >> sys.stderr, '\nwaiting for the next event'
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        # Handle inputs
        for s in readable:

            if s is server:
                # A "readable" server socket is ready to accept a connection
                connection, client_address = s.accept()
                print >> sys.stderr, 'new connection from', client_address
                connection.setblocking(0)
                inputs.append(connection)

                # Give the connection a queue for data we want to send
                message_queues[connection] = Queue.Queue()
            else:
                data = s.recv(1024)
                if data:
                    # A readable client socket has data
                    print >> sys.stderr, 'received "%s" from %s' % (data, s.getpeername())
                    # Add output channel for response
                    if s not in outputs:
                        outputs.append(s)
                    replyMessage = processMsg(data)
                    message_queues[s].put(replyMessage)

                else:
                    # Interpret empty result as closed connection
                    print >> sys.stderr, 'closing', client_address, 'after reading no data'
                    # Stop listening for input on the connection
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()

                    # Remove message queue
                    del message_queues[s]
                    # Handle outputs
        for s in writable:
            try:
                next_msg = message_queues[s].get_nowait()
            except Queue.Empty:
                # No messages waiting so stop checking for writability.
                print >> sys.stderr, 'output queue for', s.getpeername(), 'is empty'
                outputs.remove(s)
            else:
                print >> sys.stderr, 'sending "%s" to %s' % (next_msg, s.getpeername())
                s.send(next_msg)
                # Handle "exceptional conditions"
        for s in exceptional:
            print >> sys.stderr, 'handling exceptional condition for', s.getpeername()
            # Stop listening for input on the connection
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()

            # Remove message queue
            del message_queues[s]
