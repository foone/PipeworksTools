import struct
def unpackRead(f,pattern):
	length=struct.calcsize(pattern)
	data=f.read(length)
	return struct.unpack(pattern,data)


def unpackAt(buf, offset, pattern):
	length=struct.calcsize(pattern)
	return struct.unpack(pattern, buf[offset:offset+length])

def readToNull(f):
	out=[]
	x=f.read(1)
	while x!='\0' and x!='':
		out.append(x)
		x=f.read(1)
	return ''.join(out)

def peek(f):
	old_pos=f.tell()
	out=f.read(1)
	f.seek(old_pos)
	return out

def skipIf(f,value):
	if peek(f)==value:
		f.read(1)
		return True
	else:
		return False