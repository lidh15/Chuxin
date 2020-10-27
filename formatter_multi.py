import os
import subprocess
import time

from utils import N

os.chdir(os.getcwd())
processnum = 30
subnum = N // processnum
ps = []
t0 = time.time()
for i in range(processnum):
    ps.append(subprocess.Popen(f'python formatter.py {i*subnum+i//2:d} {(i+1)*subnum+(i+1)//2:d}', shell=True))
while any([not p.poll() == 0 for p in ps]):
    time.sleep(180)
print(time.time()-t0)
