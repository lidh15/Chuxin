import json
import os
from shutil import copyfile
import numpy as np

from game_branch import Game

datapath = './data/'
rawpath = datapath + 'paipus/'
newpath = datapath + 'output/'
uuids = os.listdir(rawpath)
for uuid in uuids:
    print(uuid)
    with open(rawpath+uuid, encoding='utf-8') as src:
        record = json.loads(src.readline())['record']
    g = Game(jsonrecord=record)
    flag = 1
    gameEnd = 0
    while True:
        # try:
        #     g.checkRound()
        # except:
        #     e = 'check failed '+uuid+' round %d'%g.recordid
        #     print(e)
        #     with open('formatter.log', 'a') as logfile:
        #         logfile.writelines([e+'\n'])
        #     flag = 0
        #     g.recorddata.close()
        #     break
        # finally:
        #     pass
        # try:
        #     gameEnd = g.runRound()
        # except Exception as e:
        #     print('run failed at round %d'%g.recordid, repr(e))
        #     flag = 0
        #     g.recorddata.close()
        #     break
        # finally:
        #     if gameEnd:
        #         g.recorddata.close()
        #         break
        g.checkRound()
        gameEnd = g.runRound()
        if gameEnd:
            g.recorddata.close()
            break
    if flag:
        copyfile('tmp.h5', newpath+uuid+'.h5')
    # break
