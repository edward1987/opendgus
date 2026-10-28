import re,sys
lines=open(sys.argv[1]).read().splitlines()
reg={}
def R(r):
    return {'cl':'ecx','dl':'edx','al':'eax','bl':'ebx','cx':'ecx','dx':'edx','ax':'eax'}.get(r,r)
def off(s):
    m=re.search(r'\+ (0x[0-9a-f]+|\d+)\]',s); return int(m.group(1),0) if m else 0
for L in lines:
    m=re.match(r'([0-9a-f]+): (\S+) ?(.*)',L)
    if not m: continue
    a,op,args=m.groups()
    if op in('cmp','je','jmp','jne') : print(a,op,args); continue
    ops=[x.strip() for x in args.split(',')]
    if op=='mov' and ops[1]=='dword ptr [ebp + 0x10]': reg[ops[0]]='OUT'; continue
    if op=='mov' and ops[1]=='dword ptr [ebp + 0xc]': reg[ops[0]]='IN'; continue
    if op in('movzx','mov') and len(ops)==2 and 'ptr [' in ops[1] and ops[0] in ('ecx','edx','eax','cl','dl','al'):
        base=re.search(r'\[(\w+)',ops[1]).group(1)
        if reg.get(base)=='IN':
            w='w' if 'word' in ops[1] else 'b'
            reg[R(ops[0])]=f'in{w}[{off(ops[1])//(2 if w=="w" else 1)}{"" if w=="w" else " (byte)"}]'; continue
    if op=='sar' and R(ops[0]) in reg: reg[R(ops[0])]+=f'>>{ops[1]}'; continue
    if op=='and' and R(ops[0]) in reg: reg[R(ops[0])]=f'({reg[R(ops[0])]})&{ops[1]}'; continue
    if op=='shl' and R(ops[0]) in reg: reg[R(ops[0])]=f'({reg[R(ops[0])]})<<{ops[1]}'; continue
    if op in('add','or') and R(ops[0]) in reg: reg[R(ops[0])]=f'({reg[R(ops[0])]}) {op} {reg.get(R(ops[1]),ops[1])}'; continue
    if op=='mov' and ops[0].startswith('byte ptr ['):
        base=re.search(r'\[(\w+)',ops[0]).group(1)
        if reg.get(base)=='OUT':
            src=reg.get(R(ops[1]),ops[1])
            print(f'   Data[{off(ops[0])}] = {src}')
            continue
    if op not in ('push','pop','lea','rep','call'): print('  ?',a,op,args)
