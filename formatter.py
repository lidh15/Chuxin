import logging
import os
import sys
import tarfile
import time

from tqdm import tqdm

from players import RecorderText as Recorder
from utils import N, finder

if __name__ == '__main__':
    logging.basicConfig(filename='recorder.log', level=logging.DEBUG)
    arg = sys.argv[1:]
    start = 0
    end = N
    bar = 1
    batchsize = 100
    if len(arg):
        start = int(arg[0])
        end = int(arg[1])
        bar = 0
        batchsize = 5076
    datapath = '/mnt/d/Chuxin/data/'
    recorder = Recorder(datapath=datapath)
    uuids = os.listdir(recorder.rawpath)
    uuids.sort()
    formatted = os.listdir(''.join([datapath, 'output/txt/']))
    formatted.sort()
    pbar = tqdm(total=len(uuids)) if bar else None
    success = 0
    t0 = time.time()
    for cnt, uuid in enumerate(uuids[start:end]):
        try:
            success += 1
            if finder(formatted, ''.join([uuid, '.txt'])):
                continue
            recorder.runGame(uuid)
        except:
            success -= 1
            logging.error(f'formatting failed {uuid:s}')
        finally:
            recorder.reset()
        if cnt % batchsize == batchsize - 1:
            t1 = time.time()
            batchcnt = (cnt + 1) // batchsize
            logging.info(f'{cnt+1:d} uuids checked, {success:d} formatted in {t1-t0:.2f}s')
            if not pbar is None:
                pbar.update(batchsize)
                pbar.set_description(f'batch time: {t1-t0:.2f}s')
            t0 = t1

            # Seems that tar is not meaningful.
            # for filetype in ['npy', 'txt']:
            #     path = f'{datapath:s}output/{filetype:s}/'
            #     tar = tarfile.open(f'backup/{filetype:s}/{batchcnt:04d}.tar.gz', 'w:gz')
            #     for name in os.listdir(path):
            #         filename = ''.join([path, name])
            #         tar.add(filename)
            #     tar.close()
