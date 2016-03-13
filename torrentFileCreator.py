import os
import math
import sys

# input: filename
# output: content of .torrent file to be created
fileInfo = os.stat(sys.argv[1])
print "trackers-127.0.0.1:20001"
print "name-" + sys.argv[1]
print "length-" + str(fileInfo.st_size)
num_pieces = int(math.ceil(fileInfo.st_size)) / (512 * 1024)
print "pieces-" + str(num_pieces)
