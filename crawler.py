import os
import subprocess

from utils import finder

BATCHSIZE = 10000
TIMEOUT = 20000 # depend on your network
outputpath = '../data/majsoul/0/'


with open('gamedata.txt') as src:
    uuids = src.readlines()
hook = uuids[-1]
uuids = sorted(uuids[:-1])
os.chdir('./output/crawler/')
collected = sorted(os.listdir(outputpath+'paipus/'))
batch = []
for i, uuid in enumerate(uuids):
    if not (i % BATCHSIZE):
        print('checked %d'%i)
    if not finder(collected, uuid.split('":"')[2].split('","')[0]):
        batch.append(uuid)
        if len(batch) == BATCHSIZE:
            # a batch
            batch.append(hook)
            with open(outputpath+'gamedata.txt', 'w') as target:
                target.writelines(batch)
            p = subprocess.Popen('MajsoulPaipuCrawler.exe --auto=true')
            p.wait(TIMEOUT)
            
            with open('crawler.log', 'a') as logFile:
                logFile.writelines(['downloaded %d\n'%i])
            batch = []
# final batch
batch.append(hook)
with open(outputpath+'gamedata.txt', 'w') as target:
    target.writelines(batch)
p = subprocess.Popen('MajsoulPaipuCrawler.exe --auto=true')
p.wait(TIMEOUT)

os.remove(outputpath+'paipus/'+hook)
os.remove(outputpath+'raw/'+hook)
