import Queue
import select
import socket
import sys


def process_msg(input_msg):
    """

    :param input_msg:
    :return:
    """
    flag = True
    peer_list_reply = "TRACKER_RESPONSE-"
    input_msg = input_msg.strip('\n')
    input_msg = input_msg.strip(' ')
    inputs = input_msg.split('-')

    if inputs[0] == 'REQUEST_PEERS':
        msg_body = inputs[1].split(',')
        # filename = msgBody[1].split(':')[1]
        filename = "tracker-ips"
        host, port = msg_body[0].split(':')
        with open(filename, 'rw') as f:
            for line in f:
                line = line.strip('\n')
                print line
                if flag:
                    flag = False
                    peer_list_reply += line
                else:
                    peer_list_reply = peer_list_reply + ',' + line
                    # createFile(filename,host+':'+port)

    return peer_list_reply


def create_file(file_name, peer):
    """

    :param file_name:
    :param peer:
    """
    f = open(file_name, 'a')
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
                # receive data from connection
                data = s.recv(1024)
                if data:
                    # A readable client socket has data
                    print >> sys.stderr, 'received "%s" from %s' % (data, s.getpeername())

                    # Add output channel for response
                    if s not in outputs:
                        outputs.append(s)

                    # add reply to queue
                    reply_message = process_msg(data)
                    message_queues[s].put(reply_message)

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
                # get message from queue
                next_msg = message_queues[s].get_nowait()

            except Queue.Empty:
                # No messages waiting so stop checking for writes.
                print >> sys.stderr, 'output queue for', s.getpeername(), 'is empty'
                outputs.remove(s)

            else:
                # send message on connection
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
