import glob,os
from file_utils import *
import sys,subprocess

FORMATS={
	0:'GX_TF_I4',
	1:'GX_TF_I8',
	2:'GX_TF_IA4',
	3:'GX_TF_IA8',
	4:'GX_TF_RGB565',
	5:'GX_TF_RGB5A3',
	6:'GX_TF_RGBA8',
	8:'GX_TF_C4',
	9:'GX_TF_C8',
	0xA:'GX_TF_C14X2',
	0xE:'GX_TF_CMPR',
}

def get_texture_name(path):
	globs=[]
	prefix=path.split('-')[0]
	for suffix in ('-36@*','-32@*'):
		globs.extend(glob.glob(prefix+suffix))
	return globs[0]


def decode_format(x):
	return '{}({})'.format(FORMATS.get(x,'UNKNOWN'),x)

for path in glob.glob('textures/*-64@*.dat'):
	print path
	with open(path,'rb') as f:
		fmtId,nWidth,nHeight,nOriginalWidth,nOriginalHeight,nUsageFlags,nMips=unpackRead(f,'>LHHHHBB')
		print('format: {}'.format(decode_format(fmtId)))
		print('nWidth/nHeight: {}x{}'.format(nWidth,nHeight))
		print('nOriginalWidth/nOriginalHeight: {}x{}'.format(nOriginalWidth,nOriginalHeight))
		print('nUsageFlags: {}'.format(nUsageFlags))
		print('nMips: {}'.format(nMips))
		print
		if '--convert' in sys.argv:
			altpath=get_texture_name(path)

			pngpath=altpath+'.png'
			if os.path.exists(pngpath):
				continue
			subprocess.check_call([sys.executable,'convert_image.py','-f{}'.format(texture_format),str(w),str(h),altpath])