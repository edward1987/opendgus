import struct,sys
def rva2off(secs,rva):
    for va,vs,raw,rs in secs:
        if va<=rva<va+max(vs,rs): return rva-va+raw
def main(p):
    d=open(p,'rb').read()
    pe=struct.unpack_from('<I',d,0x3c)[0]
    mach,nsec,_,_,_,optsz,_=struct.unpack_from('<HHIIIHH',d,pe+4)
    opt=pe+24; magic=struct.unpack_from('<H',d,opt)[0]
    dd=opt+(96 if magic==0x10b else 112)
    dirs=[struct.unpack_from('<II',d,dd+8*i) for i in range(16)]
    secs=[]; so=opt+optsz
    for i in range(nsec):
        name=d[so+40*i:so+40*i+8].rstrip(b'\0').decode()
        vs,va,rs,raw=struct.unpack_from('<IIII',d,so+40*i+8); secs.append((va,vs,raw,rs))
    print(p,'machine',hex(mach),'CLR' if dirs[14][1] else 'native')
    erva,esz=dirs[0]
    if esz:
        o=rva2off(secs,erva)
        _,_,_,_,nm,base,nf,nn,af,an,ao=struct.unpack_from('<IIHHIIIIIII',d,o)
        fa=rva2off(secs,af); na=rva2off(secs,an); oa=rva2off(secs,ao)
        for i in range(nn):
            n=struct.unpack_from('<I',d,na+4*i)[0]; s=d[rva2off(secs,n):].split(b'\0')[0].decode()
            ordi=struct.unpack_from('<H',d,oa+2*i)[0]
            print('  export',ordi+base,s,hex(struct.unpack_from('<I',d,fa+4*ordi)[0]))
    irva,isz=dirs[1]
    if isz:
        o=rva2off(secs,irva)
        while True:
            olt,_,_,nm,ft=struct.unpack_from('<IIIII',d,o)
            if nm==0: break
            print('  import',d[rva2off(secs,nm):].split(b'\0')[0].decode()); o+=20
for p in sys.argv[1:]: main(p)
