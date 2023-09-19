import argparse,sys,struct
from PIL import Image

def loadChunkRGB5A3(cdata):
	tile=Image.new('RGBA',(4,4))
	for y in range(4):
		for x in range(4):
			off=(y*4+x)*2
			pvalue=struct.unpack('>H',cdata[off:off+2])[0]
			if pvalue & 0x8000:
				r=((pvalue&0b0111110000000000)>>10)*255//31
				g=((pvalue&0b0000001111100000)>> 5)*255//31
				b=((pvalue&0b0000000000011111)    )*255//31
				a=255
			else:
				r=((pvalue&0b0000111100000000)>> 8)*255//15
				g=((pvalue&0b0000000011110000)>> 4)*255//15
				b=((pvalue&0b0000000000001111)    )*255//15
				a=((pvalue&0b0111000000000000)>>12)*255//7
			tile.putpixel((x,y),(r,g,b,a))
	return tile

def loadChunkRGBA8(cdata):
	tile=Image.new('RGBA',(4,4))
	for y in range(4):
		for x in range(4):
			r=ord(cdata[1+x*2+y*8])
			g=ord(cdata[32+x*2+y*8])
			b=ord(cdata[33+x*2+y*8])
			a=ord(cdata[x*2+y*8])
			tile.putpixel((x,y),(r,g,b,a))
	return tile

def loadChunkRGBA8NoWonk(cdata):
	tile=Image.new('RGBA',(4,4))
	for y in range(4):
		for x in range(4):
			r=ord(cdata[3+(x+y*4)*4])
			g=ord(cdata[2+(x+y*4)*4])
			b=ord(cdata[1+(x+y*4)*4])
			a=ord(cdata[0+(x+y*4)*4])
			tile.putpixel((x,y),(r,g,b,a))
	return tile

def loadChunkI8(cdata):
	tile=Image.new('RGBA',(8,4))
	for y in range(4):
		for x in range(8):
			i=ord(cdata[(y*8+x)])
			tile.putpixel((x,y),(i,i,i,0xFF))
	return tile

def loadChunkIA8(cdata):
	tile=Image.new('RGBA',(4,4))
	for y in range(4):
		for x in range(4):
			i=ord(cdata[1+(y*4+x)*2])
			a=ord(cdata[(y*4+x)*2])
			tile.putpixel((x,y),(i,i,i,a))
	return tile

def decodeRGB565(v):
	r=((v&0b1111100000000000)>>11)*255//31
	g=((v&0b0000011111100000)>> 5)*255//63
	b=((v&0b0000000000011111)    )*255//31
	return (r,g,b,255)

def interpolate(a,b,amt):
	iamt=1-amt
	return tuple([int(amt*v0+iamt*v1) for (v0,v1) in zip(a,b)])

def loadSubChunkCMPR(scdata):
	c0v,c1v,cmap=struct.unpack('>HHL',scdata)
	c0=decodeRGB565(c0v)
	c1=decodeRGB565(c1v)
	if c0v>c1v:
		c2=interpolate(c0,c1,2.0/3.0)
		c3=interpolate(c0,c1,1.0/3.0)
	else:
		c2=interpolate(c0,c1,0.5)
		c3=(0,0,0,0)
	colors=(c0,c1,c2,c3)
	tile=Image.new('RGBA',(4,4))
	for y in [3,2,1,0]:
		for x in [3,2,1,0]:
			ci=(cmap&0b11)
			cmap=cmap>>2
			tile.putpixel((x,y),colors[ci])
	return tile


def loadChunkCMPR(cdata):
	tile=Image.new('RGBA',(8,8))
	tile.paste(loadSubChunkCMPR(cdata[ 0: 8]),(0,0))
	tile.paste(loadSubChunkCMPR(cdata[ 8:16]),(4,0))
	tile.paste(loadSubChunkCMPR(cdata[16:24]),(0,4))
	tile.paste(loadSubChunkCMPR(cdata[24:32]),(4,4))
	return tile 

def convertRGB8(w,h,data):
	return metaparse_flex(4,4,w,h,data,(4*4*4),loadChunkRGBA8)

def convertRGB5A3(w,h,data):
	return metaparse_flex(4,4,w,h,data,(4*4*2),loadChunkRGB5A3)

def convertI8(w,h,data):
	return metaparse_flex(8,4,w,h,data,(8*4),loadChunkI8)

def convertIA8(w,h,data):
	return metaparse_flex(4,4,w,h,data,(4*4*2),loadChunkIA8)

def convertCMPR(w,h,data):
	return metaparse_flex(8,8,w,h,data,(8*8//2),loadChunkCMPR)


def metaparse_flex(cw,ch,w,h,data,chunk_size,load_chunk_func):
	num_w_chunks = (w+(cw-1))//cw
	num_h_chunks = (h+(ch-1))//ch
	total_chunks=num_w_chunks*num_h_chunks
	needed_size=total_chunks*chunk_size
	if len(data)<needed_size:
		print>>sys.stderr,"Not enough bytes! Needed {}, only have {}".format(needed_size,len(data))
		sys.exit(1)
	im=Image.new('RGBA',(w,h))
	try:
		stride = (w+(cw-1))//cw
		if stride==0:
			stride = 1 
	except ZeroDivisionError:
		stride = 1
	for chunki in range(total_chunks):
		offset=chunk_size*chunki
		cdata=data[offset:offset+chunk_size]
		tile=load_chunk_func(cdata)
		ypos=chunki//stride
		xpos=chunki%stride
		im.paste(tile,(xpos*cw,ypos*ch))
	return im

def metaparse(w,h,data,chunk_size,load_chunk_func):
	num_h_chunks = (w+3)//4
	num_w_chunks = (h+3)//4
	total_chunks=num_w_chunks*num_h_chunks
	needed_size=total_chunks*chunk_size
	if len(data)<needed_size:
		print>>sys.stderr,"Not enough bytes! Needed {}, only have {}".format(needed_size,len(data))
		sys.exit(1)
	im=Image.new('RGBA',(w,h))
	for chunki in range(total_chunks):
		offset=chunk_size*chunki
		cdata=data[offset:offset+chunk_size]
		tile=load_chunk_func(cdata)
		ypos=chunki//(w//4)
		xpos=chunki%(w//4)
		im.paste(tile,(xpos*4,ypos*4))
	return im

def image_format(s):
	s=s.lower()
	if s=='rgb5a3' or s=='5':
		return convertRGB5A3
	if s=='rgba8' or s=='6':
		return convertRGB8
	if s=='i8' or s=='1':
		return convertI8
	if s=='ia8' or s=='3':
		return convertIA8
	if s=='cmpr' or s=='14':
		return convertCMPR
	raise ValueError("Not a known format type!")

if __name__=='__main__':
	parser = argparse.ArgumentParser(
                    prog='Convert RGB5A3',
                    description='Converts RGB5A3 image files')
	parser.add_argument('width',type=int)
	parser.add_argument('height',type=int)
	parser.add_argument('filename')
	parser.add_argument('output_filename',nargs='?',help='If not present, uses filename+".png"')
	parser.add_argument('--format','-f',default='rgb5a3',help="Image format/number. Known types: rgb5a3,rgba8",type=image_format)
	args = parser.parse_args()
	if args.output_filename is None:
		args.output_filename=args.filename+'.png'
	with open(args.filename,'rb') as f:
		data=f.read()
	im = args.format(args.width, args.height, data)
	im.save(args.output_filename)