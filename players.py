import json
import os

import h5py
import numpy as np

from game_npless import Game

MAX_ROUNDS = 50
MAX_ACTIONS = 5000
COLORS = {'m':0, 'p':9, 's':18, 'z':27}

class Recorder(object):
    def __init__(self, datapath='./data/', rawsuffix='paipus/', newsuffix='output/'):
        super(Recorder, self).__init__()
        self.datapath = datapath
        self.rawpath = ''.join([datapath, rawsuffix])
        self.newpath = ''.join([datapath, newsuffix])
        self.tmpname = 'tmp.h5'
        self.uuids = os.listdir(self.rawpath)
        
        self.buffer = (np.zeros([5, 64, 34]), np.zeros([4, 4, 34]), np.zeros([7, 4], dtype='int'))
        
        self.stateSize = {
            # observable info
            'bet':         1, # integer, 0
            'repeat':      1, # integer, 1
            'direction':   1, # integer, 2
            'doraid':      1, # numtile, 3
            'points':      4, # integer, 4
            'discarddora': 4, # integer, 8
            'showndora':   4, # integer, 12
            'clear':       4, # boolean, 16
            'riichi':      4, # boolean, 20
            'isdealer':    4, # boolean, 24
            'river':       4, # numtile, 28
            'shown':       4, # numtile, 32
            # partial observable
            'dora':        4, # integer, oracle, 36
            'hands':       4, # numtile, oracle, 40
            'unfixed':     4, # numtile, oracle, 44
            'mountain':    16,# numtile, oracle, 48
        }
        self.masks = np.ones([4, 64, 34]) # positions of not observable info
        for i in range(4):
            self.masks[i, :36] = 0
            self.masks[i, 36+i:48:4] = 0

    def runGame(self, uuid):
        """Simulate a game based on the json record

        Args:
            uuid (str): uuid of a game
        
        Returns:
            boolean: True if check passed
        """
        with open(''.join([self.rawpath, uuid]), encoding='utf-8') as src:
            self.recordjson = json.loads(src.readline())['record']
        recordjson = self.recordjson
        
        tmppath = ''.join([self.newpath, self.tmpname])
        self.recorddata = h5py.File(tmppath, 'w')
        recorddata = self.recorddata
        
        recorddata.create_dataset('statesCnt', \
            shape=(1, 2), data=np.zeros([1, 2]), maxshape=(MAX_ACTIONS, 2), dtype='i', chunks=True, compression="gzip")
        recorddata.create_dataset('states', \
            shape=(0, 4, 64, 34), maxshape=(MAX_ACTIONS, 4, 64, 34), dtype='f', chunks=True, compression="gzip")
        recorddata.create_dataset('decisions', \
            shape=(0, 3, 4, 34), maxshape=(MAX_ACTIONS, 3, 4, 34), dtype='f', chunks=True, compression="gzip")
        recorddata.create_dataset('dos', \
                shape=(0, 7, 4), maxshape=(MAX_ACTIONS, 7, 4), dtype='i', chunks=True, compression="gzip")
        
        gameEnd = 0
        self.game = Game(agents=self.players)
        game = self.game
        
        for _ in range(MAX_ROUNDS):
            gameEnd = game.runRound(mountainParser(recordjson[game.roundid+1]['yama']))
            self.checkRound(gameEnd)
            if gameEnd:
                recorddata.close()
                os.rename(tmppath, ''.join([self.newpath, uuid, '.h5']))
                return True
            recorddata['statesCnt'].resize(recorddata['statesCnt'].shape[0] + 1, 0)
            recorddata['statesCnt'][-1] = [recorddata['statesCnt'][-2].sum(), 0]
        # TODO log overflow
        raise Exception('Rounds overflow!')

    def players(self):
        """Action step of all the players
        
        Returns:
            discardDecisions ((4, 34) float): which tile to discard
            chowDecisions ((4, 34) float): which meld to chow
            kongDecisions ((4, 34) float): which meld to kong
            chowDos ((4,) boolean): chow or not
            pongDos ((4,) boolean): pong or not
            kongDos ((4,) boolean): kong or not
            ronDos ((4,) boolean): ron or not
            riichiDos ((4,) boolean): riichi or not
            liujuDos ((4,) boolean): nn or not
            redfives ((4,) boolean): show red five or not
        """
        recorddata = self.recorddata
        recorded = recorddata['states'].shape[0]
        recorddata['statesCnt'][-1, 1] += 1
        
        for item in ['states', 'decisions', 'dos']:
            recorddata[item].resize(recorded + 1, 0)
        
        game = self.game
        buffer0, buffer1, buffer2 = self.buffer
        buffer1 *= 0
        buffer2 *= 0
        state = buffer0[-1]
        # 记录当前牌局状态
        state[0] = game.bet / 2
        state[1] = game.repeat / 2
        state[2] = game.direction
        doraid = game.doraid
        state[3, doraid] = 1
        tilestart = game.tilethis
        tileend = tilestart + game.leftnum
        mountainview = buffer1[-1]
        for i in range(4):
            for j in game.mountain[tilestart+i:tileend+i]:
                mountainview[i, j%34] += 1
        for player in range(4):
            state[4+player] = game.points[player]
            state[8+player] = sum([game.rivercnt[player][i] for i in doraid])
            state[12+player] = sum([game.showncnt[player][i] for i in doraid])
            state[16+player] = game.clear[player]
            state[20+player] = game.riichi[player]
            state[24+player] = game.dealer == player
            state[28+player] = game.rivercnt[player]
            state[32+player] = game.showncnt[player]
            # partial observable
            state[36+player] = game.dora[player]
            state[40+player] = game.handscnt[player]
            state[44+player] = game.unfixedcnt[player]
            state[48+player] = mountainview[player]
            state[52+player] = mountainview[player-1]
            state[56+player] = mountainview[player-2]
            state[60+player] = mountainview[player-3]
        
        states = buffer0[:-1]
        # 四人分别记录状态
        for player in range(4):
            states[player] = state
            states[player, 4:8] = np.tanh(
                (states[player, 4:8] - states[player, 4+player]) / 8000
            )
        recorddata['states'][-1] = states
        
        discardDecisions = buffer1[0]
        chowDecisions = buffer1[1]
        kongDecisions = buffer1[2]
        
        chowDos = buffer2[0]
        pongDos = buffer2[1]
        kongDos = buffer2[2]
        ronDos = buffer2[3]
        riichiDos = buffer2[4]
        liujuDos = buffer2[5]
        redfives = buffer2[6]
        
        recordjson = self.recordjson
        recordthis = recorded - recorddata['statesCnt'][-1, 0]
        roundid = game.roundid
        action = recordjson[roundid]['action'][recordthis]
        actionType = action[0]
        if actionType == 'A': # 切
            player = int(action[1])
            discardDecisions[player, tileParser(action[2:4])] = 1
            # action[4] 1/0：摸切/手切，action[5] 1/0：立直/不立直
            riichiDos[player] = int(action[5])
            redfives[player] = action[2] == '0'
        elif actionType == 'B': # 摸
            actionnext = recordjson[roundid]['action'][recordthis+1]
            if actionnext[0] == 'X': # 自摸
                ronDos[int(actionnext[2])] = 1
        elif actionType == 'C': # 吃、碰、明杠
            player = int(action[4])
            redfives[player] = '0' in action[5::2]
            idxmod = tileParser(action[5:7])
            alen = len(action)
            if idxmod == tileParser(action[7:9]):
                if alen == 11:
                    assert idxmod == tileParser(action[9:])
                    kongDos[player] = 1
                    recordjson[roundid]['action'].pop(recordthis+1)
                elif alen == 9:
                    pongDos[player] = 1
                else:
                    raise Exception('Unknown action '+action)
            else:
                assert alen == 9
                chowDecisions[player, idxmod] = 1
                chowDos[player] = 1
        elif actionType == 'D': # 暗杠、加杠
            player = int(action[1])
            # action[4] 1/0：暗杠/加杠
            kongDecisions[player, tileParser(action[2:4])] = 1
            kongDos[player] = 1
        elif actionType == 'X': # 和
            ronDos[int(action[2])] = 1
            actionnext = recordjson[roundid]['action'][recordthis+1]
            if actionnext[0] == 'X': # 双响
                ronDos[int(actionnext[2])] = 1
                actionnextnext = recordjson[roundid]['action'][recordthis+2]
                if actionnextnext[0] == 'X': # 三响
                    ronDos[int(actionnextnext[2])] = 1
        elif actionType == 'Y': # 流局
            liujuDos[game.playerthis] = action[1] == '9'
        elif actionType == 'Z': # 结算
            pass
        else:
            raise Exception('Unknown action '+action)
        recorddata['decisions'][-1] = buffer1[:-1]
        recorddata['dos'][-1] = buffer2
        
        return discardDecisions, chowDecisions, kongDecisions, \
            chowDos, pongDos, kongDos, ronDos, riichiDos, liujuDos, redfives

    def checkRound(self, gameEnd):
        """Check if the simulation is according to the record

        Args:
            gameEnd (boolean): True if the game is ended
        """
        recordjson = self.recordjson
        game = self.game
        points = np.array(game.points)
        if gameEnd:
            assert all(
                [int(pt) for pt in recordjson[game.roundid]['action'][-1][1:].split('|')] == points
            )
        else:
            roundid = game.roundid + 1
            assert recordjson[roundid]['east'] == game.dealer
            assert recordjson[roundid]['honba'] == game.repeat
            assert recordjson[roundid]['kyoutaku'] == game.bet
            assert recordjson[roundid]['round'] == game.dealer + game.direction * 4
            assert all(recordjson[roundid]['point'] == points)
    
def mountainParser(yama):
    cnt = np.zeros([4, 34], dtype='int')
    mountain = []
    for i in range(4 * 34):
        n = int(yama[i*2])
        c = COLORS[yama[i*2+1]]
        if n:
            cntcnt = cnt[:3, n+c-1].sum()
            cnt[cntcnt, n+c-1] = 1
            idx = cntcnt * 34 + n + c - 1
        else:
            cnt[3, 4+c] = 1
            idx = 3 * 34 + 4 + c
        mountain.append(idx)
    return mountain

def tileParser(tile):
    n = int(tile[0])
    c = COLORS[tile[1]]
    return n + c - 1 if n else 4 + c

if __name__ == "__main__":
    recorder = Recorder()
    uuids = os.listdir(recorder.rawpath)
    for uuid in uuids:
        print(uuid)
        recorder.runGame(uuid)
