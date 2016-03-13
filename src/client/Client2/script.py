import os
import sys
import math

fileInfo = os.stat(sys.argv[1])
pieces = int(math.ceil((fileInfo.st_size)/(512.0*1024)))

filename = sys.argv[1]
filename = filename.split(".")[0] + ".vec"

f = open("./bitvector/" + filename , "w")
str1 = ''

for i in xrange(pieces):
	str1 = str1 + "1"

f.write(str1)	
f.close

print "trackers-127.0.0.1:20001"
print "name-"+sys.argv[1]
print "length-"+str(fileInfo.st_size)
print "pieces-"+str(pieces)
