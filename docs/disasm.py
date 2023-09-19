import sys,struct
sys.path.append('../bundles')
from file_utils import *
SIGNATURE="PWK Virtual machine module v3.01 (big endian)   \x1a"
OPCODE_NAMES={
	0x64: 'pvm_First',
	0x64: 'pvm_PushLocal',
	0x65: 'pvm_PushArg',
	0x66: 'pvm_PushGlobal',
	0x67: 'pvm_PushConstant',
	0x68: 'pvm_PushNull',
	0x69: 'pvm_PushCodeAddr',
	0x6a: 'pvm_PushInt',
	0x6b: 'pvm_Switch',
	0x6c: 'pvm_Pop',
	0x6d: 'pvm_Dup',
	0x6e: 'pvm_EnterFrame',
	0x6f: 'pvm_Operator',
	0x70: 'pvm_SwitchTable',
	0x71: 'pvm_CallMember',
	0x72: 'pvm_CallMemberNO',
	0x73: 'pvm_BranchIf',
	0x74: 'pvm_BranchIfNot',
	0x75: 'pvm_Jump',
	0x76: 'pvm_CallCast',
	0x77: 'pvm_TypeConvertToLocal',
	0x78: 'pvm_TypeConvertLocalFrom',
	0x79: 'pvm_CopyToLocal',
	0x7a: 'pvm_MemberAccess',
	0x7b: 'pvm_ArrayAccess',
	0x7c: 'pvm_ReturnValue',
	0x7d: 'pvm_Return',
	0x7e: 'pvm_Yield',
	0x7f: 'pvm_NoOps',
	0x80: 'pvm_BreakBit',
	0x7f: 'pvm_OpMask'
}
def opcode_name(x):
	if x in OPCODE_NAMES:
		return OPCODE_NAMES[x]
	else:
		return ''

def get_opcode_size(code, ip):
	OPCODE_SIZES={
		0x64:3,
		0x65:2,
		0x66:5,
		0x67:5,
		0x68:1,
		0x69:5,
		0x6a:5,
		0x6c:2,
		0x6d:2,
		0x71:3,
		0x72:3,
		0x73:5,
		0x74:5,
		0x75:5,
		0x76:5,
		0x77:7,
		0x78:3,
		0x79:3,
		0x7a:3,
		0x7b:1,
		0x7c:1,
		0x7d:1,
		0x7e:1,
		0x7f:1
	}
	current_opcode = ord(code[ip])&0x7f
	if current_opcode in OPCODE_SIZES:
		return OPCODE_SIZES[current_opcode]
	elif current_opcode==0x6e:
		p=(ip+4)&0xfffffffc
		return (unpackAt(code, p+2, '>H')[0] -1)*8 + (p-ip) + 0xC;
	elif current_opcode==0x6f:
		v=unpackAt(code, ip+4, '>H')[0]
		if v<2:
			return 7
		if 1<v-6:
			if v==2:
				return 3
			if v!=4:
				return 3
		return 7
	elif current_opcode==0x70:
		return (unpackAt(code,ip+1,'>H')[0]*8 + ((ip+6)&0xfffffff)+4)-ip
	else:
		return -1

def read_symbol_name(f, name_offset):
	global_fpos=f.tell()
	f.seek(symbol_table_offset+name_offset)
	symbol_name=readToNull(f)
	print("symbol_name={!r}".format(symbol_name))
	f.seek(global_fpos)
	return symbol_name


with open(sys.argv[1],'rb') as f:
	sig=f.read(0x31)
	if sig!=SIGNATURE:
		print(sys.stderr,"Invalid signature! '{}'".format(sig))
		sys.exit()

	f.seek(0x38)
	code_offset,code_length,variables_length_offset=unpackRead(f,'>LLL')
	print('code_offset={} code_length={} variables_length_offset={}'.format(code_offset,code_length,variables_length_offset))
	f.seek(code_offset)
	code=f.read(code_length)
	
	# read variables 
	f.seek(variables_length_offset)
	num_variables,variables_length=unpackRead(f,'>HH')
	print('num_variables={} variables_length={}'.format(num_variables,variables_length))
	
	# read types 
	f.seek(0x58)
	types_offset=unpackRead(f,'>L')[0]
	print("types_offset={}".format(types_offset))
	f.seek(types_offset)
	types_length=unpackRead(f,'>L')[0]
	print("types_length={}".format(types_length))
	
	# read symbol table 
	f.seek(0x68)
	symbol_table_offset=unpackRead(f,'>L')[0]
	print("symbol_table_offset={}".format(symbol_table_offset))
	f.seek(types_offset+4)
	for type_index in range(types_length):
		start_fpos=f.tell()
		this_type_type,unk1,this_type_length=unpackRead(f,'>BBH')
		print("type#{} this_type_type={} unk1={} this_type_length={}".format(type_index, this_type_type,unk1,this_type_length))
		#type 0 is probably scalar 
		#type 1 is... struct? 
		#type 2 is array
		#type 3 is reference
		if this_type_type not in (2,3):
			symbol_name_offset = unpackRead(f,'>L')[0]
			symbol_name=read_symbol_name(f,symbol_name_offset)

		f.seek(start_fpos+this_type_length)
	
	# read globals 
	f.seek(0x48)
	globals_offset=unpackRead(f,'>L')[0]
	print("globals_offset={}".format(globals_offset))
	f.seek(globals_offset)
	globals_count,globals_b,globals_c=unpackRead(f,'>LLL')
	print("globals_count={} globals_b={} globals_c={} ".format(globals_count,globals_b,globals_c))
	for global_index in range(globals_count):
		global_name_offset,global_flags,global_type=unpackRead(f,'>LHH')
		print("global#{} global_name_offset={} global_flags={} global_type={} ".format(global_index, global_name_offset,global_flags,global_type))
		symbol_name=read_symbol_name(f,global_name_offset)


	# read members
	f.seek(0x60)
	members_offset=unpackRead(f,'>L')[0]
	print("members_offset={}".format(members_offset))
	f.seek(members_offset)
	members_count=unpackRead(f,'>L')[0]
	print("members_count={}".format(members_count))
	for member_index in range(members_count):
		member_ptr,member_unk,symbol_offset=unpackRead(f,'>HHL')
		print("member_ptr={} member_unk={} symbol_offset={}".format(member_ptr,member_unk,symbol_offset))
		symbol_name=read_symbol_name(f,symbol_offset)

	ip=0
	stack=[]
	while True:
		current_opcode = ord(code[ip])&0x7f
		opsize=get_opcode_size(code,ip)
		print('IP: {:08x} OPCODE: {:02x} {} OPCODE_SIZE={}'.format(ip, current_opcode,opcode_name(current_opcode),opsize))
		ip+=1
		if current_opcode==0x66: # call
			function=unpackAt(code,ip,'>L')[0]+12
			print('SHOULD CALL {:08x}'.format(function))
			ip+=4
		elif current_opcode==0x67: # push 32bit
			value=unpackAt(code,ip,'>L')[0]+12
			print('PUSHING {:08x}'.format(value))
			stack.append(value)
			ip+=4
		elif current_opcode==0x6c: # pop
			value=unpackAt(code,ip,'>B')[0]
			print('POPPING {:08x}'.format(value))
			[stack.pop() for x in range(value)]
			ip+=1
		elif current_opcode==0x6f: # operator
			op1,op2 = unpackAt(code,ip,'>BB')
			print('OPERATOR OP1={:02x} OP2={:02x}'.format(op1,op2))
			ip+=2
		elif current_opcode==0x6E: # start function?
			p=(ip+3)&0xfffffffc
			offset=p+(unpackAt(code,p+2,'>h')[0]-1) * 8 + 12 
			#print(p,offset)
			#ip=offset # wait why are we following the jump? are we a disassembler or interpreter? 
			#sys.exit()
#		elif current_opcode==0x7d: # return/pop frame
#			pass
		else:
			if opsize==-1:
				print('Opsize is negative! aborting')
				sys.exit()
			ip-=1
			ip+=opsize
