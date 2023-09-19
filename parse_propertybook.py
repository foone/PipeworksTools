import glob,os,sys
from file_utils import *
import sys,subprocess


PROP_STRING=2
PROP_PROPERTY_SET=13

PROPERTY_TYPE = {
	0: 'PROP_INT',
	1: 'PROP_FLOAT',
	PROP_STRING: 'PROP_STRING',
	3: 'PROP_POINT3',
	4: 'PROP_POINT2',
	10: 'PROP_XFORMR3',
	11: 'PROP_COLOR',
	PROP_PROPERTY_SET: 'PROP_PROPERTY_SET',
	14: 'PROP_COLOR32',
}

def read_header(f):
	f.seek(32)
	nVersion,nSets,nTrueSize,nResourceLocks = unpackRead(f,'>LLLL')
	nsb = nTrueSize + 4 
	f.seek(nTrueSize)
	extra_sizes = unpackRead(f,'>L')[0]
	if extra_sizes != 0:
		# I have no idea what this means 
		nsb = (nTrueSize + 19) & 0xfffffff0 
	str_table_offset = (extra_sizes * 16) + nsb

	point_data_offset = nsb

	info = {
		'nVersion': nVersion,
		'nSets': nSets,
		'nTrueSize': nTrueSize,
		'nResourceLocks': nResourceLocks,
		'nsb': nsb,
		'str_table_offset': str_table_offset,
		'point_data_offset': point_data_offset
	}
	print info 
	return info 

def read_strings(f, header):
	f.seek(header['str_table_offset'])
	nStrings = unpackRead(f,'>L')[0]
	print('num_strings: {}'.format(nStrings))
	string_offsets = unpackRead(f,'>{}L'.format(nStrings))
	print string_offsets
	out=[]
	for i,offset in enumerate(string_offsets):
		f.seek(header['str_table_offset']+offset)
		s=readToNull(f)#.decode('utf-8')
		out.append(s)
		print i,s
	return out

def safe_index(list, n):
	try:
		return list[n]
	except IndexError:
		return '?'
def format_depth(n):
	return '--'*n

def decode_prop(f, depth=0):
	value_offset = f.tell()+4
	propType,propFlags,nTagLength,propValue,pName=unpackRead(f,'>BBHlL')
	tagname=''
	display_name = name = safe_index(strings,pName)
	if (propFlags&1)!=0:
		tagname=name[:nTagLength]
		name=name[nTagLength:]
		display_name = '{}:{}'.format(tagname,name)
	print '{}* propType={} ({}), propFlags={},nTagLength={},propValue={} (@0x{:x}),pName={}'.format(
		format_depth(depth),
		PROPERTY_TYPE.get(propType,''),propType,
		propFlags,
		nTagLength,
		(propValue if propType!=PROP_STRING else '"{}" ({})'.format(safe_index(strings,propValue),propValue)),
		value_offset,
		(pName if (propFlags&3)==0 else '"{}" ({})'.format(display_name,pName)),
	)
	return propType,propFlags,nTagLength,propValue,pName

def meta_decode_prop(f,depth=0):
	starting_offset = f.tell()
	propType,propFlags,nTagLength,propValue,pName=decode_prop(f,depth)
	if propType == PROP_PROPERTY_SET:
		property_table_offset = starting_offset + propValue
		f.seek(property_table_offset)
		vt,pParent,pTemplate,nTotalProps,nNamedProps=unpackRead(f,'>LlLHH')
		print('{}vt={},pParent={},pTemplate={},nTotalProps={},nNamedProps={}'.format(
			format_depth(depth),
			vt,pParent,pTemplate,nTotalProps,nNamedProps
		))
		props=unpackRead(f,'>{}l'.format(nTotalProps))
		if pTemplate == 1:
			pTemplate = 0
			pParent = property_table_offset + pParent # SIGNED POINTERS! COME OUT AND TRY IT
			#parents.append(pParent)
			
			for prop_offset in props:
				f.seek(property_table_offset+prop_offset)
				meta_decode_prop(f,depth+1)


def read_triples(f, strings, header):
	f.seek(56)
	prop_sets=[]
	offsets = unpackRead(f,'>{}L'.format(header['nSets']))
	parents=[]
	for offset in offsets:
		f.seek(offset)
		meta_decode_prop(f,0)


if __name__ == '__main__':
	with open(sys.argv[1],'rb') as f:
		header=read_header(f)
		strings=read_strings(f, header)
		triples=read_triples(f, strings, header)