import select
import socket
import sys
import Queue
import os
import time
from thread import *
from collections import defaultdict

uploadInfos = defaultdict(dict) # For seeders
downloadInfos = defaultdict(dict) # For leechers
pieceRequestQueue = defaultdict(dict) # For leechers

PIECE_SIZE = 1024*512
BLOCK_SIZE = 4*1024
DELIMITER = '|/!@#$%^&*\|'
SEPAERATOR = '|/<>?\~|'
lastBuffered = ''

fd = None

badaFlag = False
torrentInfo = {}
pieceBitVector = {}
seeder = True
count = 0
myHost= ""
myPort = 0
inputs = []
#	inputs = []
	# Sockets to which we expect to write
outputs = []
	# Outgoing message queues (socket:Queue)
message_queues = {}


def getKey(item):
	return item[0]

def returnPeerList(torrentInfo,host,port):
	connected = False
	for tracker in torrentInfo['trackers'] :
		print tracker
		tracker = tracker.strip('\n')
		hostTracker,portTracker = tracker.split(':')
		server_address = (hostTracker, int(portTracker))

		msg = "REQUEST_PEERS-"+host+":"+str(port)+",FILE:"+torrentInfo['name']
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		print   'connecting to %s port %s' % server_address
		
		try:
			s.connect(server_address)
			print  '%s: sending "%s"' % (s.getsockname(), msg)
			s.send(msg)
			connected = True
			break
		except:
			print "Unable to Connect"
			pass
	if connected :
		data = s.recv(BLOCK_SIZE)
		print "Received data:" + data
		data = data.split('-')
		peerList = data[1].split(',')
		print peerList
		return peerList
	else:
		return []

	
def parseTorrentFile(inp):
	global trackers,torrentName

	with open(inp) as f:
		for line in f:
			info = line.strip(' ')
			info = line.strip('\n')
			info = line.split('-')
			if info[0] == 'trackers'	:
				torrentInfo['trackers'] = info[1].split(',')
			elif info[0] == 'name':
				torrentInfo['name'] = info[1]
			elif info[0] == 'length':
				torrentInfo['length'] = int(info[1])
			elif info[0] == 'pieces':
				torrentInfo['pieces'] = int(info[1])
			else :
				print "Torrent File Corrupted\n"
				sys.exit(0)
def processData(data):
	response = ''
	header = data.split(':')[0]
	if header == "REQUEST_FILE":
		pass
	elif header == "HAVE":
		pass
	elif header == "":
		pass

def availablePieces():
	return 10

def processMsg(data):
	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue
	response = ''
	data = data.split(SEPAERATOR)
	Q = Queue.Queue()
	header = data[0]
	if header == "REQUEST_FILE":
		currentPiece = 1
		count = 0
		pieceFlag = True
		f=open (data[1].strip('\n'), "rb") 

		fileInfo = os.stat(data[1].strip('\n'))
		fileSize = fileInfo.st_size

		pieces = fileSize/2
		offset = 1	#for 1st seeder and this for 2nd seeder
		#offset = (pieces/PIECE_SIZE)*PIECE_SIZE + 1
		f.seek(offset)
		msg = "OFFSET"+SEPAERATOR+str(offset)
	#	Q.put(msg)
		l = f.read(BLOCK_SIZE)

		while (l and pieceFlag):
			Q.put(l)    
			l = f.read(BLOCK_SIZE)
			count = count+1
			if(count/10 == currentPiece):
				print "Piece "+str(currentPiece) +" put in queue for senting to leecher"
				currentPiece = currentPiece +1
			if(currentPiece == pieces/PIECE_SIZE and offset == 0):
				pieceFlag = False 

		f.close()
		response = "Queue"
		ret = (response, Q)
	elif header == "HAVE":
		pass
	return ret

def handleRecvIO(s,file,length):

	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue
	count = 1
	percent = 100
	offset = 0
	f = open(file, "wb")
	f.seek(offset)
	print "Ready to Recieve : "+file
	while(count<=length):
		part = s.recv(BLOCK_SIZE)
		f.write(part)
		count=count+1
		if count == length/percent :
			print ""+str(percent)+" Percent Remaining"
			if percent != 1 :
				percent = percent-1		 
	f.close()
	print file + " Downloaded Successfully"

def pieceRequestOrdering(filename):
	filename = filename.strip("\n")
	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue,inputs
	for x in xrange(1,int(torrentInfo["pieces"])+1):
		pieceRequestQueue[filename][x] = Queue.Queue()
	print inputs
	tempList = inputs[1:]
	for s in tempList:
		print "Hello"
		if s in downloadInfos[filename]:
			bitvector = downloadInfos[filename][s]
			index = 1
			for i in bitvector:
				if i =='1':
					pieceRequestQueue[filename][index].put(s)
					index = index + 1
					print index


	#print pieceRequestQueue[filename]
	#TO DO
	#Message format
	#Create message and put msg in the outut message queue
def retrieveBytesFromFile(s,filename,index):
	global PIECE_SIZE,BLOCK_SIZE
	filename = filename.strip('\n')
	print filename
	offset = 0
	try:
		fo = open(filename, "r+b")
		print "Reading File at index : " + str(index)

		fo.seek((index-1)*PIECE_SIZE, 0)

		print "current file position is : "+  str(fo.tell())
		# print "Name of the file: ", fo.name
		# fo.seek((index-1)*PIECE_SIZE, 0)
		for blockNumber in xrange(0,PIECE_SIZE/BLOCK_SIZE):
			print "In Loop"
			byteData = fo.read(BLOCK_SIZE)
			
			if(byteData==''):
				print "byteData is NULL"
				break
			print "current file position is : "+ str(fo.tell())
			if(byteData):
				data = "HAVE_PIECE"+SEPAERATOR+filename+SEPAERATOR+str(index)+SEPAERATOR+str(blockNumber)+SEPAERATOR+byteData+DELIMITER

				message_queues[s].put(data)
		fo.close()
	except:
		print "Error Handling File "
		pass
	


def processRecvdMsg(data,s):

	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue,badaFlag,fd
#	print   'received "%s" from %s' % (data, s.getpeername())
	data = data.strip('\n')
	temp = data.split(SEPAERATOR)
	header = temp[0]
	data = "" 

	if header == "RECEIVE_FILE":
		file = temp[1]
		length = int(temp[2])
		handleRecvIO(s,file,length)
		# running = False
		pass
	elif header == "REQUEST_FILE":	
		response, Q = processMsg(data)
		if response == "Queue":
			length = Q.qsize()
			msg = "RECEIVE_FILE"+SEPAERATOR+ temp[1] +SEPAERATOR+str(length)+SEPAERATOR
			message_queues[s].put(msg)
			while(not Q.empty()):
				message_queues[s].put(Q.get_nowait())
	elif header == "HANDSHAKE":
		filename = temp[1]
		bitvector = temp[2]
		print bitvector
		print "Hello"
		pieces = len(bitvector)
		# uploadInfos[filename][s.getpeername()] = bitvector
		uploadInfos[filename][s] = bitvector

		bitvector =  returnBitVector(filename,pieces)
		data = "REPLY_HANDSHAKE"+SEPAERATOR+filename+SEPAERATOR+stringify(bitvector)+DELIMITER
		message_queues[s].put(data)

	elif header == "REPLY_HANDSHAKE":
		filename = temp[1]
		bitvector = temp[2]
		pieces = len(bitvector)
		downloadInfos[filename][s] = bitvector
		if(not os.path.exists(filename)):	
			fd= open(filename,"w+b",0)
			fd.close()
		fd = open(filename,"rw+b",0)

		#uploadInfos[filename][s] = bitvector 
	elif header == "REQUEST_PIECE" :
		print temp
		filename = temp[1]
		index = int(temp[2])
		actualPieceData = retrieveBytesFromFile(s,filename,index)

	elif header == "HAVE_PIECE":
		filename = temp[1]
		index = int(temp[2])
		blockNumber = int(temp[3])
		byteData = temp[4]
		print len(temp)
		print len(byteData)
		try:
			# if(not os.path.exists(filename)):	
			# 	fd = open(filename,"wb+")
			# 	fd.close()
			# fd = open(filename,"rwb+")
			position = PIECE_SIZE*(index-1) + blockNumber*BLOCK_SIZE

			fd.seek(position,0)
			writtenAmount = fd.write(byteData)
			#time.sleep(0.001)
			fd.flush()
			print "Downloaded index = " +str(index) + " blockNumber = "+str(blockNumber)+" for filename = "+filename + " at position: " + str(position) + " till: " + str(fd.tell()) + " Written = "+str(writtenAmount)
		except:
			print "Error handling while Flushing data"
		if(index == 13 and blockNumber==25):
			badaFlag = True
			fd.close()
	else:
		print "data count: "  + data
		

	if s not in outputs:
		outputs.append(s)

def handShaking(peerList):

	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue
	for peers in peerList:
		print peers
		host,port = peers.split(':')
		port = int(port)
		peerServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			peerServer.connect((host,port))
			# peerServer.setblocking(0)
			outputs.append(peerServer)
			print "Connection to "	+ peers + " succeeded"
			print "Creating output queue for "+ peers
			message_queues[peerServer] = Queue.Queue()
			
			data = "HANDSHAKE"+SEPAERATOR+torrentInfo['name'] +SEPAERATOR+stringify(pieceBitVector[torrentInfo["name"]])+DELIMITER
			
			peerServer.send(data)
			print peerServer.getpeername()	
			print "Hello"		
			try:
				data = peerServer.recv(BLOCK_SIZE)
				print   'received "%s" from %s' % (data, peerServer.getpeername())
				print data
				processRecvdMsg(data,peerServer)
			except:
				print "Error while recieveing "
			inputs.append(peerServer)
			
		except:
			print "Some error"
			pass
		peerServer.setblocking(0)	
	
def rarestPieceFirstAlgo(filename,pieces):
	filename = filename.strip('\n')
	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue
	
	# Creating list of tuples for rarest first order (pieceCount,pieceIndex)
	countPiece = []
	for i in xrange(1,pieces+1):
		countPiece.append((pieceRequestQueue[filename][i].qsize(),i))

	sorted(countPiece, key=getKey)
	for tuples in countPiece:
		pieceQsize = tuples[0]
		pieceIndex = tuples[1]
		# FORMAT of Sending message
		
		if pieceQsize != 0 :
			data = "REQUEST_PIECE"+SEPAERATOR+filename+SEPAERATOR+str(pieceIndex)+DELIMITER
			s = pieceRequestQueue[filename][pieceIndex].get_nowait()
			message_queues[s].put(data)



def reactor(server):

	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue,inputs,outputs,message_queues,DELIMITER,lastBuffered,badaFlag
	running = True
	while running:

		# Wait for at least one of the sockets to be ready for processing
		print   '\nwaiting for the next event using select'

		readable, writable, exceptional = select.select(inputs, outputs, inputs)
			# Handle inputs
		for s in readable:
			print "In Readable"
			if s is server:
				# A "readable" server socket is ready to accept a connection
				connection, client_address = s.accept()
				print   'new connection from', client_address
				connection.setblocking(0)
				inputs.append(connection)
				outputs.append(connection)
				# Give the connection  a queue for data we want to send
				message_queues[connection] = Queue.Queue()
			else:
				bufferMsg = s.recv(BLOCK_SIZE)

				if bufferMsg:
					if lastBuffered != "":
						bufferMsg = lastBuffered + bufferMsg 
						lastBuffered = ""

					if badaFlag :
						print "Stray data is bufferMsg = "+bufferMsg
					bufferMsg = bufferMsg.split(DELIMITER)
					if badaFlag :
						print " bufferMsgafter splitting DELIMITER= " + ('').join(bufferMsg)
					if(bufferMsg[-1]):
						lastBuffered = bufferMsg[-1]
					for data in bufferMsg[:-1]:
						processRecvdMsg(data,s)
					# A readable client socket has data
					
				else:
					# Interpret empty result as closed connection
					print   'closing', client_address, 'after reading no data'
					# Stop listening for input on the connection
					if s in outputs:
							outputs.remove(s)
					inputs.remove(s)
					s.close()

					# Remove message queue
					del message_queues[s]
						# Handle outputs
		for s in writable:
			print "In writable"
			try:
				next_msg = message_queues[s].get_nowait()
			except:
				# No messages waiting so stop checking for writability.
				print   'output queue for', s.getpeername(), 'is empty'
				outputs.remove(s)
			else:
				temp = next_msg.split(SEPAERATOR)
				if(temp[0] == "HAVE_PIECE"):
					print "Sending data for file = " + temp[1] +" PieceIndex = "+temp[2]+ " blockNumber = "+temp[3] 
					#print   'sending "%s" to %s' % (next_msg, s.getpeername())
				s.send(next_msg)
				#time.sleep(0.075)
					# Handle "exceptional conditions"
		for s in exceptional:
			print "In Exceptional"
			print   'handling exceptional condition for', s.getpeername()
			# Stop listening for input on the connection
			inputs.remove(s)
			if s in outputs:
				outputs.remove(s)
			s.close()

			# Remove message queue
			del message_queues[s]

def recvMessage(host,port,peerList):

	global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue
	print "Entering recvMessage"
	global count
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.setblocking(0)
	# Bind the socket to the port
	server_address = (host, port)
	print   'starting up on %s port %s' % server_address
	server.bind(server_address)
	count = count+1
	# Listen for incoming connections
	server.listen(5)
	inputs.append(server)
	# Sockets from which we expect to read

	handShaking(peerList)

			
	if not seeder :
		pieceRequestOrdering(torrentInfo["name"])
		rarestPieceFirstAlgo(torrentInfo["name"],int(torrentInfo['pieces']))

	reactor(server)

def returnBitVector(filename,pieces):
	global seeder
	if seeder:
		return [True]*pieces

	return [False]*(pieces)

def stringify(bitvector):
	str = ""
	for i in bitvector :
		if(i == False):
			str = str +'0'
		else:
			str = str +'1'
	return str

def initialize():
	global myHost,myPort,seeder,peerList,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue
	if(len(sys.argv) < 3):
		print "To run please follow following Format: python %s hostname port (optional:Torrent File)",sys.argv[0]
		sys.exit("Bye")
	seeder = True	
	myHost = sys.argv[1]
	myPort = int(sys.argv[2])
	peerList = []
	if len(sys.argv) == 4:
		filename = sys.argv[3]
		parseTorrentFile(filename)
		torrentInfo["name"] = torrentInfo["name"].strip('\n')
		bitvector = returnBitVector(torrentInfo["name"],int(torrentInfo["pieces"]))
		pieceBitVector[torrentInfo["name"]] = bitvector
		seeder = False

	if(not seeder):
		peerList = returnPeerList(torrentInfo,myHost,myPort)
		print "Peer List Received"
	
# Create a TCP/IP socket
if __name__ == '__main__':

#Tracker connection
	initialize()
	try:
		start_new_thread(recvMessage,(myHost,myPort,peerList))	
	#	start_new_thread(sendMessage,(host,port,peerList))
	except:
		print "Error: unable to start thread"
while 1:
	pass