import sys,re
data=open(sys.argv[1],'rb').read()
minl=int(sys.argv[2]) if len(sys.argv)>2 else 5
for m in re.finditer(rb'[\x20-\x7e]{%d,}'%minl,data): print('A %x %s'%(m.start(),m.group().decode()))
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}'%minl,data): print('U %x %s'%(m.start(),m.group().decode('utf-16le')))
