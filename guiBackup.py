from wx import wx
from wx.lib.pubsub import Publisher
#######################################################################################

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
torrentInfo = defaultdict(dict) # For storing torrentInfo for every file running
sizeDownloaded = defaultdict(dict) #total size download corresponding to each file
Downloading = defaultdict(dict)  #flag for each file.
# inputs = defaultdict(dict)
# outputs = defaultdict(dict)

PIECE_SIZE = 1024*512
BLOCK_SIZE = 4*1024
DELIMITER = '|/!@#$%^&*\|'
SEPAERATOR = '|/<>?\~|'
lastBuffered = ''

fd = None

running = True
badaFlag = False
# torrentInfo = {}
pieceBitVector = {}
seeder = True
count = 0
myHost= ""
myPort = 0
inputs = []
outputs = []

pieceStatus = []  # stores status of pieces. If all the pieces are downloaded, turn running = False;
numPiecesDownloaded=0

# Outgoing message queues (socket:Queue)
message_queues = {}


def getSize(filename):
    print "In getSize"
    filename = "./"+filename
    print "retrieving size of file:  " + filename
    
    size = os.path.getsize( filename )
    print "Size is: " + str(size)
    # if size < 0:
    #     import subprocess as s
    #     size = long( s.Popen("ls -l %s | cut -d ' ' -f5" % filename,
    #                 shell=True, stdout=s.PIPE).communicate()[0] )
    return size

def getKey(item):
    return item[0]

def returnPeerList(torrentInfo,host,port,currentFile):
    connected = False
    for tracker in torrentInfo[currentFile]['trackers'] :
        print tracker
        tracker = tracker.strip('\n')
        hostTracker,portTracker = tracker.split(':')
        server_address = (hostTracker, int(portTracker))

        msg = "REQUEST_PEERS-"+host+":"+str(port)+",FILE:"+torrentInfo[currentFile]['name']
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
    currentFile=""
    with open(inp) as f:
        for line in f:
            info = line.strip(' ')
            info = line.strip('\n')
            info = line.split('-')
            if info[0] == 'name':
                currentFile = info[1].split('\n')[0]

    with open(inp) as f:
        for line in f:
            info = line.strip(' ')
            info = line.strip('\n')
            info = line.split('-')
            if info[0] == 'trackers'    :
                torrentInfo[currentFile]['trackers'] = info[1].split(',')
            elif info[0] == 'name':
                torrentInfo[currentFile]['name'] = info[1]
            elif info[0] == 'length':
                torrentInfo[currentFile]['length'] = int(info[1])
            elif info[0] == 'pieces':
                torrentInfo[currentFile]['pieces'] = int(info[1])
            else :
                print "Torrent File Corrupted\n"
                sys.exit(0)
    return currentFile

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
        offset = 1  #for 1st seeder and this for 2nd seeder
        #offset = (pieces/PIECE_SIZE)*PIECE_SIZE + 1
        f.seek(offset)
        msg = "OFFSET"+SEPAERATOR+str(offset)
    #   Q.put(msg)
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

#generates the queue
def pieceRequestOrdering(filename, currentFile):
    filename = filename.strip("\n")
    global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue,inputs, outputs
    for x in xrange(1,int(torrentInfo[currentFile]["pieces"])+1):
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

#read from file and send blocks to the requesting peer
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
    
#handles different messages
def processRecvdMsg(data,s):

    global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue,badaFlag,fd,pieceStatus,sizeDownloaded, inputs, outputs
    #print   'received "%s" from %s' % (data, s.getpeername())
    data = data.strip('\n')
    temp = data.split(SEPAERATOR)
    currentFile = temp[1]
    print "In processRecvdMsg"
    print currentFile
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
        # print "piece status list: " + (' ').join(pieceStatus)
        # print pieceStatus
        print len(temp)
        print len(byteData)
        sizeDownloaded[filename] += len(byteData) 
        try:
            # if(not os.path.exists(filename)): 
            #   fd = open(filename,"wb+")
            #   fd.close()
            # fd = open(filename,"rwb+")
            position = PIECE_SIZE*(index-1) + blockNumber*BLOCK_SIZE

            fd.seek(position,0)
            writtenAmount = fd.write(byteData)
            #time.sleep(0.001)
            fd.flush()

            pieceStatus[index-1] = pieceStatus[index-1] + 1
            if(pieceStatus[index-1]==128):
                numPiecesDownloaded = numPiecesDownloaded + 1

            print "Downloaded index = " +str(index) + " blockNumber = "+str(blockNumber)+" for filename = "+filename + " at position: " + str(position) + " till: " + str(fd.tell()) + " Written = "+str(writtenAmount)
        except:
            print "Error handling while Flushing data"
    else:
        # print "data count: "  + data
        pass
        
    if s not in outputs:
        outputs.append(s)

#send handshake message to the peers and recv handshake_reply
#transfers bitvector to each other
def handShaking(peerList, currentFile):

    global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue, pieceStatus, inputs, outputs
    if not seeder:
        pieceStatus = [0]*torrentInfo[currentFile]['pieces']   #if a piece value reaches 128, that piece has been downloaded
        print "Seeder in handshaking"
    for peers in peerList:
        print peers
        host,port = peers.split(':')
        port = int(port)
        peerServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            peerServer.connect((host,port))
            # peerServer.setblocking(0)
            outputs.append(peerServer)
            print "Connection to "  + peers + " succeeded"
            print "Creating output queue for "+ peers
            message_queues[peerServer] = Queue.Queue()
            
            data = "HANDSHAKE"+SEPAERATOR+torrentInfo[currentFile]['name'] +SEPAERATOR+stringify(pieceBitVector[torrentInfo[currentFile]["name"]])+DELIMITER
            
            peerServer.send(data)
            print peerServer.getpeername()  
            print "Hello"       
            try:
                data = peerServer.recv(BLOCK_SIZE)
                print   'received "%s" from %s' % (data, peerServer.getpeername())
                # print data
                processRecvdMsg(data,peerServer)
            except:
                print "Error while recieveing "
            inputs.append(peerServer)
            
        except:
            print "Some error"
            pass
        peerServer.setblocking(0)   

#request messages are put in the message queue corresponding to the peers
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

#called by recvMessage
def reactor(server, currentFile):

    global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue,inputs,outputs,message_queues,DELIMITER,lastBuffered,badaFlag,running,numPiecesDownloaded, Downloading, sizeDownloaded
    Downloading[currentFile] = True
    sizeDownloaded[currentFile] = 0
    while Downloading[currentFile]:
        #In case of a leecher, an initial check to whether the file has been downloaded
        if not seeder:
            # print "Size Downloaded : " + str(sizeDownloaded[currentFile])
            if(getSize(currentFile)==int(torrentInfo[currentFile]['length'])):
                Downloading[currentFile] = False
                print currentFile + " downloaded Successfully"

                #TO DO here:
                #call some dialog box saying "Download completed for the currentFile"
                #Close sockets gracefully
                fd.close()
                break
                # try:
                #     for s in inputs:
                #         if s is not server:
                #             s.close()
                #     for s in outputs:
                #         if s is not server:
                #             s.close()
                # except:
                #     print "Error while closing sockets"

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
            del message_queues[s]   #reactor is called by recvMessage

#thread runs here
def recvMessage(host,port,peerList, currentFile):

    global seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue, inputs, outputs
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
    # if(not seeder)
    inputs = []
    outputs = []
    print "currentFile is : " + currentFile
    print "inputs is : " + str(type(inputs))
    print "outputs is : " + str(type(outputs))

    inputs.append(server)
    # Sockets from which we expect to read

    handShaking(peerList, currentFile)

    if not seeder :  
        pieceRequestOrdering(torrentInfo[currentFile]["name"], currentFile)
        rarestPieceFirstAlgo(torrentInfo[currentFile]["name"],int(torrentInfo[currentFile]['pieces']))


    reactor(server, currentFile)    #Thread first calls this function
    print "Closing Main Socket"
    server.close()

#bitvector showing which pieces I have. '0' means piece missing and '1' means I have the piece.
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

def initialize(torrentFile):
    global myHost,myPort,seeder,torrentInfo,uploadInfos,downloadInfos,pieceRequestQueue
    # if(len(sys.argv) < 3):
    #     print "To run please follow following Format: python %s hostname port (optional:Torrent File)",sys.argv[0]
    #     sys.exit("Bye")
    seeder = True   
    # myHost = sys.argv[1]
    # myPort = int(sys.argv[2])
    currentFile=""
    peerList = []
    if len(sys.argv) == 1:
        # filename = sys.argv[3]
        currentFile = parseTorrentFile(torrentFile)
        torrentInfo[currentFile]["name"] = torrentInfo[currentFile]["name"].strip('\n')
        bitvector = returnBitVector(torrentInfo[currentFile]["name"],int(torrentInfo[currentFile]["pieces"]))
        pieceBitVector[torrentInfo[currentFile]["name"]] = bitvector
        seeder = False

    if(not seeder):
        peerList = returnPeerList(torrentInfo,myHost,myPort, currentFile)
        print "Peer List Received"
    return (currentFile, peerList)
# if __name__ == '__main__':
#     #Tracker connection
#     initialize()
#     try:
#         start_new_thread(recvMessage,(myHost,myPort,peerList))  
#     #   start_new_thread(sendMessage,(host,port,peerList))
#     except:
#         print "Error: unable to start thread"
# while 1:
#     pass


#######################################################################################

class MyProgressDialog(wx.Dialog):
    """"""
 
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        wx.Dialog.__init__(self, None, title="Progress")
        self.count = 0
 
        self.progress = wx.Gauge(self, range=20)
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.progress, 0, wx.EXPAND)
        self.SetSizer(sizer)
 
        # create a pubsub listenerwx.
        CallAfter(Publisher().sendMessage, "update", "")
        Publisher().subscribe(self.updateProgress, "update")
 
    #----------------------------------------------------------------------
    def updateProgress(self, msg):
        """
        Update the progress bar
        """
        self.count += 1
 
        if self.count >= 20:
            self.Destroy()
 
        self.progress.SetValue(self.count)

class Example(wx.Frame):

    def __init__(self, parent, title):    
        super(Example, self).__init__(parent, title=title, 
            size=(460, 380))

        # self.InitUI()
        self.panel = wx.Panel(self)
        
        sizer = wx.GridBagSizer(5, 5)

        self.text1 = wx.StaticText(self.panel, label="BITTORRENT v1.0")
        sizer.Add(self.text1, pos=(0, 0), flag=wx.TOP|wx.LEFT|wx.BOTTOM, 
            border=15)

        self.icon = wx.StaticBitmap(self.panel, bitmap=wx.Bitmap('exec.png'))
        sizer.Add(self.icon, pos=(0, 4), flag=wx.TOP|wx.RIGHT|wx.ALIGN_RIGHT, 
            border=5)

        self.line = wx.StaticLine(self.panel)
        sizer.Add(self.line, pos=(1, 0), span=(1, 5), 
            flag=wx.EXPAND|wx.BOTTOM, border=10)

        self.text2 = wx.StaticText(self.panel, label="Port")
        sizer.Add(self.text2, pos=(3, 0), flag=wx.LEFT, border=10)

        self.portText = wx.TextCtrl(self.panel)
        sizer.Add(self.portText, pos=(3, 1), span=(1, 3), flag=wx.TOP|wx.EXPAND)

        self.text3 = wx.StaticText(self.panel, label="Torrent File")
        sizer.Add(self.text3, pos=(4, 0), flag=wx.LEFT|wx.TOP, border=10)

        self.torrentFileText = wx.TextCtrl(self.panel)
        sizer.Add(self.torrentFileText, pos=(4, 1), span=(1, 3), flag=wx.TOP|wx.EXPAND, 
            border=5)

        self.text4 = wx.StaticText(self.panel, label="IP")
        sizer.Add(self.text4, pos=(2, 0), flag=wx.LEFT|wx.TOP, border=10)

        self.IPText = wx.TextCtrl(self.panel)
        sizer.Add(self.IPText, pos=(2, 1), span=(1, 3), flag=wx.TOP|wx.EXPAND, 
            border=5)

        #default values
        self.IPText.SetValue("127.0.0.1")
        self.portText.SetValue("10001")


        self.button1 = wx.Button(self.panel, label="Browse...")
        sizer.Add(self.button1, pos=(4, 4), flag=wx.TOP|wx.RIGHT, border=5)
        self.Bind( wx.EVT_BUTTON, self.OnButton_FrameHandler, self.button1 )

        self.sb = wx.StaticBox(self.panel, label="Optional Attributes")

        boxsizer = wx.StaticBoxSizer(self.sb, wx.VERTICAL)
        boxsizer.Add(wx.CheckBox(self.panel, label="Public"), 
            flag=wx.LEFT|wx.TOP, border=5)
        boxsizer.Add(wx.CheckBox(self.panel, label="Generate Default Constructor"),
            flag=wx.LEFT, border=5)
        boxsizer.Add(wx.CheckBox(self.panel, label="Generate Main Method"), 
            flag=wx.LEFT|wx.BOTTOM, border=5)
        sizer.Add(boxsizer, pos=(5, 0), span=(1, 5), 
            flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT , border=10)

        self.button3 = wx.Button(self.panel, label='Help')
        sizer.Add(self.button3, pos=(7, 0), flag=wx.LEFT, border=10)

        self.button4 = wx.Button(self.panel, label="Start")
        sizer.Add(self.button4, pos=(7, 3))
        self.Bind( wx.EVT_BUTTON, self.OnClickStart, self.button4 )

        self.button5 = wx.Button(self.panel, label="Exit")
        sizer.Add(self.button5, pos=(7, 4), span=(1, 1),  
            flag=wx.BOTTOM|wx.RIGHT, border=5)
        self.Bind( wx.EVT_BUTTON, self.OnClickExit, self.button5 )


        sizer.AddGrowableCol(2)
        self.panel.SetSizer(sizer)
        self.Centre()
        self.Show()     

    def OnButton_FrameHandler(self,event):
        #print "Hello"
        openFileDialog = wx.FileDialog(self, "Open Torrent file", "", "",
                                       "Torrent files (*.torrent)|*.torrent", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if openFileDialog.ShowModal() == wx.ID_CANCEL:
            return    
        else:
            paths = openFileDialog.GetPaths()

        self.torrentFileText.SetValue(paths[0])


    def OnClickExit(self,event):
        running = False
        self.Destroy()

    def OnClickStart(self,event):
        myHost = self.IPText.GetValue()
        myPort = int(self.portText.GetValue())
        torrentFilename = self.torrentFileText.GetValue()

        (currentFile, peerList) = initialize(torrentFilename)
        try:
            start_new_thread(recvMessage,(myHost,myPort,peerList, currentFile))  
        except:
            print "Error: unable to start thread"

    def createProgressBar(self):
        self.count = 0
        self.progress = wx.Gauge(self, range=20)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.progress,2,  
            flag=wx.EXPAND, border=5)
        self.SetSizer(sizer)
        Publisher().subscribe(self.updateProgress, "update")

    def updateProgress(self, msg):
        """
        Update the progress bar
        """
        self.count += 1
 
        if self.count >= 20:
            self.Destroy()
 
        self.progress.SetValue(self.count)
                        
    def InitUI(self):
        pass


def GUI():
    app = wx.App()
    Example(None, title="Distributed Bittorent")
    app.MainLoop()

if __name__ == '__main__':
    GUI()
#     try:
#         start_new_thread(GUI, ())
#     except:
#         print "Error: unable to start thread"
# while 1:
#     pass
   