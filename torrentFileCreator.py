import os
import math
import sys

# input: filename
# output: content of .torrent file created

fileInfo = os.stat(sys.argv[1])
print "trackers-127.0.0.1:20001"
print "name-" + sys.argv[1]
print "length-" + str(fileInfo.st_size)
pieces = int(math.ceil(fileInfo.st_size)) / (512 * 1024)
print "pieces-" + str(pieces)
