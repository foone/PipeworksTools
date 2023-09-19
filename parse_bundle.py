import struct,sys,argparse,zlib,os

from file_utils import *
Z_BEST_COMPRESSION=9
def readToNullWithFFs(f):
	out=[]
	x=f.read(1)
	while x!='\0' and x!='':
		if x=='\xFF':
			x=x+f.read(3)
		out.append(x)
		x=f.read(1)
	return ''.join(out)

def get_type_name(typenum):
	return full_file['types'][typenum]['name']

def read_chunklist(f, full_file):

	chunklist=[]

	resid_offset=full_file['header']['nResLocsOffset']
	nLocs=full_file['header']['nResEntries']
	# The res_id offset isn't defined, it's just the offset to the types header + the length of the types header 
	res_id_offset = full_file['header']['nTypesOffset'] + full_file['header']['nTypesSize']
	if args.verbose: 
		print 'ResEntries start at {}, count is {}'.format(resid_offset, nLocs)
	f.seek(res_id_offset)
	for i in range(nLocs):
		nOffset,nSizeAndType,nSizeAndCompression,nResourceId=unpackRead(f,'>4L')
		info={
			'nOffset': nOffset,
			'nSizeAndType':nSizeAndType,
			'type':nSizeAndType>>26,
			'decompressed_size':nSizeAndType&0x3ffffff,
			'nSizeAndCompression':nSizeAndCompression,
			'compression_method':(nSizeAndCompression>>26)&7,
			'compression_buffers':(nSizeAndCompression>>29),
			'compressed_size':nSizeAndCompression&0x3ffffff,
			'nResourceId':nResourceId,
		}
		chunklist.append(info)
		if args.verbose: 
			print 'nOffset', nOffset
			print 'nSizeAndType',nSizeAndType
			print 'type: {} ({})'.format(get_type_name(info['type']), info['type'])
			print 'decompressed_size',info['decompressed_size']
			print 'nSizeAndCompression',nSizeAndCompression
			print 'compression_method: {} ({})'.format(('br_None','BR_Zip')[info['compression_method']],info['compression_method'])
			print 'compressed_size',info['compressed_size']
			print 'compression_buffers',info['compression_buffers']
			print 'nResourceId: {0} (0x{0:08X})'.format(nResourceId)
			print

	return chunklist

def read_types(f, full_file):
	num_types=full_file['header']['nTypeNames']
	types_offset=full_file['header']['nTypesOffset']
	f.seek(types_offset)
	types=[]
	for i in range(num_types):
		skipped=skipIf(f,'\xFF') # I don't know what this means. So we're skipping it
		version=unpackRead(f,'>h')[0]
		name=readToNull(f)
		if args.verbose: 
			print 'Type: "{}", resourceVersion {}'.format(name, version)
		info={
			'version':version,
			'name':name,
			'skipped':skipped
		}
		types.append(info)
	return types


def read_project_name(f):
	f.seek(40)
	name=readToNull(f)
	if args.verbose: 
		print 'szProjectName:',name 
	return name

def read_signature(f):
	f.seek(0)
	sig=f.read(40)
	matches=sig=='Pipeworks bundle v1.20 (big endian)   \x1A\0'
	if args.verbose: 
		print 'szSigString:',repr(sig)
	if not matches:
		if args.verbose: 
			print 'Not a match!'
	info={
		'signature':sig,
		'matches':matches
	}
	return info 

def read_names(f, full_file):
	header = full_file['header']
	bundle_name=full_file['name']
	name_info_offset = header['nNameInfoOffset']
	name_info_size = header['nNameInfoSize']
	f.seek(name_info_offset)
	name=readToNull(f)
	if args.verbose:
		print 'Name Name:',name
	f.seek(name_info_offset+32)
	nResourceNames, nLookUpEntries =unpackRead(f,'>LL')
	if args.verbose:
		print 'nResourceNames: {}, nLookUpEntries: {}'.format(nResourceNames, nLookUpEntries)
	pLookupTableHead  = name_info_offset + 40 + nResourceNames*16
	if args.verbose:
		print 'pLookupTableHead: {}'.format(pLookupTableHead)

	f.seek(pLookupTableHead)
	str_offsets=unpackRead(f,'>{}L'.format(nLookUpEntries))
	if args.verbose:
		print 'str_offsets:',str_offsets
	new_str_offsets=[pLookupTableHead+x+nLookUpEntries*4 for x in str_offsets]
	strings=[]
	for soffset in new_str_offsets:
		f.seek(soffset)
		strings.append(readToNullWithFFs(f))
	if args.verbose:
		print 'strings:',strings
	f.seek(name_info_offset+40)
	filenames=[]
	expanded_filenames=[]
	for i in range(nResourceNames):
		# this is a ResNamePair
		nResourceId,nPathIdx,nFilenameIdx,nExtensionIdx,nLocalIdx=unpackRead(f,'>LHHHH')
		if args.verbose:
			print 'ResNamePair:'
			print '  nResourceId:   {0} (0x{0:08x})'.format(nResourceId)
			print '  nPathIdx:      {}'.format(nPathIdx)
			print '  nFilenameIdx:  {}'.format(nFilenameIdx)
			print '  nExtensionIdx: {}'.format(nExtensionIdx)
			print '  nLocalIdx:     {}'.format(nLocalIdx)
		filenames.append((nResourceId,nPathIdx,nFilenameIdx,nExtensionIdx,nLocalIdx))
		buffer='['+bundle_name+']'
		for string_id,prefix in (
			(nPathIdx,'\\'),
			(nFilenameIdx,'\\'),
			(nExtensionIdx,'.'),
			(None,'.prd'),
			(nLocalIdx,'|'),
		):
			if string_id is None or strings[string_id]!='':
				buffer+=prefix

			if string_id is not None:
				to_add = strings[string_id]
				if to_add.startswith('\xFF'):
					a,b,length=struct.unpack('xBBB',to_add[:4])
					index=((a*256 + b)*4) & 0x3fffc
					str_data = strings[a*256+b][:length]
					buffer += str_data
					to_add=to_add[4:]
				buffer+= to_add
				# TODO: handle \xFF nonsense
		expanded_filenames.append((nResourceId,buffer))
		if args.verbose:
			print '  Expanded: {}'.format(buffer)

	info={
		'to_name':{},
		'to_resid':{}
	}
	for resid, name in expanded_filenames:
		info['to_name'][resid]=name
		info['to_resid'][name]=resid

	return info


def get_filename(full_file, resid, chunk):
	# we can't parse the filenames yet so this just produces a dummy filename
	return '{:08x}-buf{}@{:08x}.dat'.format(resid,chunk['compression_buffers'],chunk['nOffset'])
	

def find_chunks(full_file, resid):
	chunks=[]
	for chunk in full_file['chunks']:
		if chunk['nResourceId']==resid:
			chunks.append(chunk)
	return chunks


def find_chunk(full_file, resid):
	chunks = find_chunks(full_file, resid)
	if len(chunks)>1:
		raise ValueError("Too many chunks!")
	elif len(chunks)==0:
		return None
	return chunks[0]

def extract_chunk(f, full_file, resid,out_path=None):
	chunks = find_chunks(full_file, resid)
	if not chunks:
		print >>sys.stderr, "Couldn't find chunk {}!".format(resid)
		return
	filenames=[]
	for chunk in chunks:
		if args.verbose:
			print >>sys.stderr,'Extracting chunk: {}'.format(chunk)
		f.seek(chunk['nOffset'])
		compressed_data=f.read(chunk['compressed_size'])
		if chunk['decompressed_size']==chunk['compressed_size']:
			decompressed_data=compressed_data
		else:
			try:
				decompressed_data = zlib.decompress(compressed_data)
			except zlib.error:
				print >>sys.stderr,"Failed to extract {}!".format(chunk)
				continue 
		out_filename=get_filename(full_file, resid, chunk)
		if out_path is not None:
			out_filename = os.path.join(out_path, out_filename)
		with open(out_filename, 'wb') as fout:
			fout.write(decompressed_data)
		filenames.append(out_filename)
def most_compress(data):
	smallest=None
	smallest_data=None
	for level in range(0,9):
		cdata=zlib.compress(data,level)
		if smallest is None or len(cdata)<smallest:
			smallest=len(cdata)
			smallest_data=cdata
	return smallest_data
def inject_chunk(full_file, resid, filename):
	chunk = find_chunk(full_file, resid)
	if chunk is None:
		print >>sys.stderr, "Couldn't find chunk {}!".format(resid)
		return
	with open(args.filename,'rb') as f:
		data=f.read()
	with open(filename,'rb') as f:
		uncompressed_data=f.read()

	compressed=most_compress(uncompressed_data)
	padding=''
	if len(compressed)>chunk['compressed_size']:
		print >>sys.stderr,'File is too big when compressed! Original compressed size is {}, new file is {}'.format(
			chunk['compressed_size'],len(compressed))
		return
	if len(compressed)<chunk['compressed_size']:
		padding=('\0'*(chunk['compressed_size']-len(compressed)))
	if args.verbose:
		print('Original compressed size: {}, new compressed size: {}'.format(len(compressed),chunk['compressed_size']))

	with open(args.filename,'wb') as f:
		f.write(data[:chunk['nOffset']])
		f.write(compressed)
		f.write(padding)
		f.write(data[chunk['nOffset']+chunk['compressed_size']:])

def find_all_textures(f, full_file):
	OUTPATH='textures'
	if not os.path.exists(OUTPATH):
		os.mkdir(OUTPATH)
	for chunk in full_file['chunks']:
		if (
			chunk['decompressed_size'] == chunk['compressed_size'] and 
			chunk['compressed_size'] == 16 and 
			chunk['cflags'] == 64
		):
			extract_chunk(f, full_file, chunk['res_id'],out_path=OUTPATH)



def hex_or_dec(x):
	if x.startswith('0x'):
		return int(x[2:],16)
	return int(x) 


def read_header(f):
	f.seek(76)
	parts=unpackRead(f,'>12L')
	NAMES=(	'nTotalSize', 'nTypeNames', 'nTypesOffset', 'nTypesSize', 
			'nResEntries', 'nResLocsOffset', 'nResReqs', 'nResReqsOffset',
			'nForkPairs', 'nForkPairsOffset', 'nNameInfoOffset', 'nNameInfoSize'
	)
	out={}
	for name,value in zip(NAMES,parts):
		if args.verbose: 
			print '{:<16s}: {}'.format(name,value)
		out[name]=value
	return out

def list_filenames(full_file):
	to_resid=full_file['names']['to_resid']
	names=list(to_resid.keys())
	names.sort()
	for name in names:
		resid=to_resid[name]
		ctype='?"'
		chunks = find_chunks(full_file, resid)
		if chunks:
			ctype=get_type_name(chunks[0]['type'])
		print '{:>10}: (0x{:08X}): "{}" ({})'.format(resid,resid,name,ctype)

if __name__=='__main__':
	parser = argparse.ArgumentParser(
                    prog='BundleParser',
                    description='Parses Pipeworks Spigot Engine bundle files')
	parser.add_argument('filename')
	parser.add_argument('--verbose','-v',help='print all kinds of pointless nonsense while parsing/extracting',
		default=False,action='store_true')
	parser.add_argument('--extract',type=hex_or_dec,metavar='RESID',help='resource ID to extract/decompress')
	parser.add_argument('--inject',type=hex_or_dec,metavar='RESID',help='resource ID to inject/decompress')
	parser.add_argument('--inject-file',type=str,metavar='FILENAME',help='filename to inject/decompress')
	parser.add_argument('--extract-textures',action='store_true',help='Extract all textures')
	parser.add_argument('--list-filenames',action='store_true',help='List all filenames')
	args = parser.parse_args()


	full_file={}
	with open(args.filename,'rb') as f:
		full_file['sig']=read_signature(f)
		if not full_file['sig']['matches']:
			if not args.verbose:
				print >>sys.stderr,"File ID signature doesn't match."
			sys.exit()

		full_file['name']=read_project_name(f)
		full_file['header']=read_header(f)
		full_file['types']=read_types(f, full_file)
		full_file['chunks']=read_chunklist(f, full_file)
		full_file['names']=read_names(f, full_file)

		if args.extract is not None:
			resid=args.extract
			extract_chunk(f,full_file, resid)
		if args.extract_textures:
			find_all_textures(f,full_file)
		if args.list_filenames:
			list_filenames(full_file)
	if args.inject is not None: 
		inject_chunk(full_file, args.inject, args.inject_file)