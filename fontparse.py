import struct,sys,argparse,zlib,json

def unpackRead(f,pattern):
	length=struct.calcsize(pattern)
	data=f.read(length)
	return struct.unpack(pattern,data)

def readToNull(f):
	out=[]
	x=f.read(1)
	while x!='\0':
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

def debugPrint(message):
	if args.verbose:
		print(message,file=sys.stderr)


if __name__=='__main__':
	parser = argparse.ArgumentParser(
                    prog='FontParser',
                    description='Parses Pipeworks Spigot Engine font files')
	parser.add_argument('filename')
	parser.add_argument('--verbose','-v',help='print all kinds of pointless nonsense while parsing/extracting',
		default=False,action='store_true')
	args = parser.parse_args()
	charmap={}
	with open(sys.argv[1],'rb') as fobj:
		texture_count=unpackRead(fobj,'>L')[0]
		debugPrint('texture_count={}'.format(texture_count))

		for i in range(texture_count):
			a,b,c=unpackRead(fobj,'>LLL')
			debugPrint('* texture {}: {:08x} {:08x} {:08x}'.format(i,a,b,c))

		debugPrint('After texture-list:')
		character_count,a,b,c,d,e,f,g,h = unpackRead(fobj,'>5Lffff')
		debugPrint('* character_count: {}'.format(character_count))
		debugPrint('* {:08x} {:08x} {:08x} {:08x} {:0.2f} {:0.2f} {:0.2f} {:0.2f}'.format(a,b,c,d,e,f,g,h))
		for chari in range(character_count):
			a,b,c,d,left,right,top,bottom,unk1,unk2=unpackRead(fobj,'>4cffffff')
			char=(a+b+c+d).decode('utf-8').rstrip('\0')
			debugPrint(u'* "{}" ({}): {:0.2f} {:0.2f} {:0.2f} {:0.2f} {:0.2f} {:0.2f}'.format(char,ord(char),left,right,top,bottom,unk1,unk2))
			charmap[char]=ord(char)
	with open('out.json','w') as f:
		json.dump(charmap,f)