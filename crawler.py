import os
import subprocess


def finder(uuids, uuid, shortest=10):
    n = len(uuids)
    if n < shortest:
        return uuid in uuids
    uuids = uuids[:n//2] if uuid < uuids[n//2] else uuids[n//2:]
    return finder(uuids, uuid)

with open('gamedata.txt') as src:
    uuids = src.readlines()
hook = uuids[-1]
uuids = sorted(uuids[:-1])
os.chdir('./output/crawler/')
outputpath = '../data/majsoul/15370948/'
collected = sorted(os.listdir(outputpath+'paipus/'))
batch = []
batchsize = 100000
timeout = batchsize * 2 # depend on your network
for i, uuid in enumerate(uuids):
    if not (i % batchsize):
        print('checked %d'%i)
    if not finder(collected, uuid.split('":"')[2].split('","')[0]):
        batch.append(uuid)
        if len(batch) == batchsize:
            # a batch
            batch.append(hook)
            with open(outputpath+'gamedata.txt', 'w') as target:
                target.writelines(batch)
            p = subprocess.Popen('MajsoulPaipuCrawler.exe --auto=true')
            p.wait(timeout)
            
            with open('crawler.log', 'a') as logFile:
                logFile.writelines(['downloaded %d\n'%i])
            batch = []
# final batch
batch.append(hook)
with open(outputpath+'gamedata.txt', 'w') as target:
    target.writelines(batch)
p = subprocess.Popen('MajsoulPaipuCrawler.exe --auto=true')
p.wait(timeout)

os.remove(outputpath+'paipus/'+hook)
os.remove(outputpath+'raw/'+hook)
