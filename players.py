import json
import logging
import os

import h5py
import numpy as np

from game_npless import Game
from utils import (IDX_TILER, MAX_ACTIONS, MAX_ROUNDS, mountainParser,
                   tileParser)

logging.basicConfig(filename='recorder.log', level=logging.DEBUG)

class Recorder(object):
    def __init__(self, tmpname='', datapath='data/', rawsuffix='paipus/', newsuffix='output/'):
        super(Recorder, self).__init__()
        self.datapath = datapath
        self.rawpath = ''.join([datapath, rawsuffix])
        self.newpath = ''.join([datapath, newsuffix])
        self.tmppath = ''.join([self.newpath, tmpname])
        self.uuids = os.listdir(self.rawpath)

        self.recordjson = None
        self.recorddata = None
        self.recordthis = 0
        self.game = None
        self.buffer = [np.zeros([4, 4, 34]), np.zeros([7, 4], dtype='int')]

    def reset(self):
        self.recordjson = None
        self.recorddata = None
        self.recordthis = 0
        self.game = None
        for buf in self.buffer:
            buf *= 0

    def checkRound(self, gameEnd):
        """Check if the simulation is according to the record

        Args:
            gameEnd (boolean): True if the game is ended
        """
        recordjson = self.recordjson
        game = self.game
        points = game.points
        self.recordthis = 0
        if gameEnd:
            assert all([int(pt_) == pt or pt == max(points) for pt_, pt in zip(recordjson[game.roundid]['action'][-1][1:].split('|'), points)])
        else:
            roundid = game.roundid + 1
            assert recordjson[roundid]['east'] == game.dealer
            assert recordjson[roundid]['honba'] == game.repeat
            assert recordjson[roundid]['kyoutaku'] == game.bet
            assert recordjson[roundid]['round'] == game.dealer + game.direction * 4
            assert all([pt_ == pt for pt_, pt in zip(recordjson[roundid]['point'], points)])

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
            action ((2,) ndarray): the idx in the buffer of the action taken
        """
        buffer = self.buffer
        bufferDecision = buffer[0]
        bufferDecision *= 0
        bufferDo = buffer[1]
        bufferDo *= 0

        discardDecisions = bufferDecision[0]
        chowDecisions = bufferDecision[1]
        kongDecisions = bufferDecision[2]
        
        chowDos = bufferDo[0]
        pongDos = bufferDo[1]
        kongDos = bufferDo[2]
        ronDos = bufferDo[3]
        riichiDos = bufferDo[4]
        liujuDos = bufferDo[5]
        redfives = bufferDo[6]

        recordjson = self.recordjson
        recordthis = self.recordthis
        game = self.game

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
            pass
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
            if not int(action[4]):
                redfives[player] = not int(action[2])
            actionnext = recordjson[roundid]['action'][recordthis+1]
            if actionnext[0] == 'X': # 抢杠
                ronDos[int(actionnext[2])] = 1
                actionnextnext = recordjson[roundid]['action'][recordthis+2]
                if actionnextnext[0] == 'X': # 双响
                    ronDos[int(actionnextnext[2])] = 1
                    actionnextnextnext = recordjson[roundid]['action'][recordthis+3]
                    if actionnextnextnext[0] == 'X': # 三响
                        ronDos[int(actionnextnextnext[2])] = 1
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
            actionlast = recordjson[roundid]['action'][recordthis-1]
            if actionlast[0] == 'X': # 自摸
                actionlastlast = recordjson[roundid]['action'][recordthis-2]
                ronDos[int(actionlastlast[1])] = 1
        else:
            raise Exception('Unknown action '+action)

        self.recordthis += 1
        action = (np.where(bufferDecision), np.where(bufferDo))

        return discardDecisions, chowDecisions, kongDecisions, \
            chowDos, pongDos, kongDos, ronDos, riichiDos, liujuDos, redfives, action

    def runGame(self, uuid):
        """Simulate a game based on the json record

        Args:
            uuid (str): uuid of a game
        
        Returns:
            boolean: True if check passed
        """
        with open(''.join([self.rawpath, uuid]), encoding='utf-8') as src:
            self.recordjson = json.loads(src.readline())['record']
        self.game = Game(agents=self.players)

        raise NotImplementedError

class RecorderHDF5(Recorder):
    def __init__(self, tmpname='tmp.h5', datapath='data/', rawsuffix='paipus/', newsuffix='output/'):
        super().__init__(tmpname, datapath, rawsuffix, newsuffix)
        self.buffer.append(np.zeros([5, 64, 34]))
        self.compression = None # 'gzip'
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
        try:
            super().runGame(uuid)
        except NotImplementedError:
            pass
        finally:
            tmppath = self.tmppath
            compression = self.compression
            self.recorddata = h5py.File(tmppath, 'w')
            recorddata = self.recorddata
            
            recorddata.create_dataset('statesCnt', \
                shape=(1, 2), data=np.zeros([1, 2]), maxshape=(MAX_ACTIONS, 2), dtype='i', chunks=True, compression=compression)
            recorddata.create_dataset('states', \
                shape=(0, 4, 64, 34), maxshape=(MAX_ACTIONS, 4, 64, 34), dtype='f', chunks=True, compression=compression)
            recorddata.create_dataset('decisions', \
                shape=(0, 3, 4, 34), maxshape=(MAX_ACTIONS, 3, 4, 34), dtype='f', chunks=True, compression=compression)
            recorddata.create_dataset('dos', \
                    shape=(0, 7, 4), maxshape=(MAX_ACTIONS, 7, 4), dtype='i', chunks=True, compression=compression)
            
            gameEnd = 0
            game = self.game
            recordjson = self.recordjson
            checkRound = self.checkRound
            for _ in range(MAX_ROUNDS):
                gameEnd = game.runRound(mountainParser(recordjson[game.roundid+1]['yama']))
                checkRound(gameEnd)
                if gameEnd:
                    recorddata.close()
                    os.rename(tmppath, ''.join([self.newpath, uuid, '.h5']))
                    return True
                recorddata['statesCnt'].resize(recorddata['statesCnt'].shape[0] + 1, 0)
                recorddata['statesCnt'][-1] = [recorddata['statesCnt'][-2].sum(), 0]
            
            logging.warning(f'Rounds overflow at {uuid:s}!')

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
        discardDecisions, chowDecisions, kongDecisions, chowDos, pongDos, kongDos, \
            ronDos, riichiDos, liujuDos, redfives, _ = super().players()

        recorddata = self.recorddata
        recorded = recorddata['states'].shape[0]
        for item in ['states', 'decisions', 'dos']:
            recorddata[item].resize(recorded + 1, 0)
        game = self.game

        bufferStates = self.buffer[-1]
        state = bufferStates[-1]
        # 记录当前牌局状态
        state[0] = game.bet / 2
        state[1] = game.repeat / 2
        state[2] = game.direction
        doraid = game.doraid
        state[3, doraid] = 1
        tilestart = game.tilethis
        tileend = tilestart + game.leftnum
        mountainview = self.buffer[0][-1]
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
        
        states = bufferStates[:-1]
        # 四人分别记录状态
        for player in range(4):
            states[player] = state
            states[player, 4:8] = np.tanh(
                (states[player, 4:8] - states[player, 4+player]) / 8000
            )
        recorddata['states'][-1] = states
        recorddata['decisions'][-1] = self.buffer[0][:-1]
        recorddata['dos'][-1] = self.buffer[1]
        recorddata['statesCnt'][-1, 1] += 1

        return discardDecisions, chowDecisions, kongDecisions, \
            chowDos, pongDos, kongDos, ronDos, riichiDos, liujuDos, redfives

class RecorderText(Recorder):
    def __init__(self, tmpname='', datapath='data/', rawsuffix='paipus/', newsuffix='output/'):
        super().__init__(tmpname, datapath, rawsuffix, newsuffix)
        self.token = {
            'bet':'BET',
            'repeat':'REP',
            'direction':'DIR',
            'doranum':'DORA',
            'isdealer':'E',
            'clear':'C',
            'riichi':'R',
            'point+':'PP',
            'point-':'PM',
            'handsdora':'HD',
            'unfixeddora':'UD',
            'riverdora':'XD',
            'showndora':'SD',
            'hands':'H',
            'unfixed':'U',
            'river':'X',
            'shown':'S',
            'mountainview':'M',
        }
        self.masks = np.ones([4, 53]) # positions of not observable info
        for i in range(4):
            self.masks[:, i:49:12] = 0
        for i in range(4):
            self.masks[i, i*12:i*12+4] = 1

    def runGame(self, uuid):
        """Simulate a game based on the json record

        Args:
            uuid (str): uuid of a game
        
        Returns:
            boolean: True if check passed
        """
        try:
            super().runGame(uuid)
        except NotImplementedError:
            pass
        finally:
            gameEnd = 0
            game = self.game
            recordjson = self.recordjson
            self.recorddata = [[], []]
            recorddata = self.recorddata
            checkRound = self.checkRound
            for _ in range(MAX_ROUNDS):
                gameEnd = game.runRound(mountainParser(recordjson[game.roundid+1]['yama']))
                checkRound(gameEnd)
                if gameEnd:
                    newpath = self.newpath
                    with open(''.join([newpath, 'txt/', uuid, '.txt']), 'w') as recordtxt:
                        recordtxt.writelines(recorddata[0])
                    np.save(''.join([newpath, 'npy/', uuid]), recorddata[1]) # .npy added automatically
                    return True
            
            logging.warning(f'Rounds overflow at {uuid:s}!')

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
        discardDecisions, chowDecisions, kongDecisions, chowDos, pongDos, kongDos, \
            ronDos, riichiDos, liujuDos, redfives, action = super().players()

        if action[0][0].size or action[1][0].size:
            game = self.game
            recordstr = []
            appender = recordstr.append

            hands = game.hands
            unfixed = game.unfixed
            river = game.river
            shown = game.shown
            handscnt = game.handscnt
            unfixedcnt = game.unfixedcnt
            rivercnt = game.rivercnt
            showncnt = game.showncnt
            clear = game.clear
            riichi = game.riichi
            doraid = game.doraid
            pointsdiff = np.zeros([4, 4], dtype='int')
            points = np.array(game.points)
            for player in range(4):
                playerstr = str(player)
                hand = hands[player]
                stri = ''.join(['H', playerstr, ' '])
                listi = [IDX_TILER[i] for i, j in enumerate(hand) if j]
                appender(''.join([stri.join(listi), 'H', playerstr]) if len(listi) else '')
                handcnt = handscnt[player]
                stri = ''.join(['HD', playerstr])
                appender(' '.join([stri for _ in range(sum([handcnt[i] for i in doraid]) + sum(hand[106:133:9]))]))

                unfixedi = unfixed[player]
                stri = ''.join(['U', playerstr, ' '])
                listi = [IDX_TILER[i] for i, j in enumerate(unfixedi) if j]
                appender(''.join([stri.join(listi), 'U', playerstr]) if len(listi) else '')
                unfixedcnti = unfixedcnt[player]
                stri = ''.join(['UD', playerstr])
                appender(' '.join([stri for _ in range(sum([unfixedcnti[i] for i in doraid]) + sum(unfixedi[106:133:9]))]))

                riveri = river[player]
                stri = ''.join(['X', playerstr, ' '])
                listi = [IDX_TILER[i] for i, j in enumerate(riveri) if j]
                appender(''.join([stri.join(listi), 'X', playerstr]) if len(listi) else '')
                rivercnti = rivercnt[player]
                stri = ''.join(['XD', playerstr])
                appender(' '.join([stri for _ in range(sum([rivercnti[i] for i in doraid]) + sum(riveri[106:133:9]))]))

                showni = shown[player]
                stri = ''.join(['S', playerstr, ' '])
                listi = [IDX_TILER[i] for i, j in enumerate(showni) if j]
                appender(''.join([stri.join(listi), 'S', playerstr]) if len(listi) else '')
                showncnti = showncnt[player]
                stri = ''.join(['SD', playerstr])
                appender(' '.join([stri for _ in range(sum([showncnti[i] for i in doraid]) + sum(showni[106:133:9]))]))

                appender(''.join(['E' if player == game.dealer else 'NE', playerstr]))
                appender(''.join(['C' if clear[player] else 'NC', playerstr]))
                appender(''.join(['R' if riichi[player] else 'NR', playerstr]))

                pointsdiff[player] = np.ceil(np.tanh((points - points[player]) / 8000) * 12)
                pdifflist = []
                for i in range(4):
                    pdiff = pointsdiff[player, i]
                    stri = ''.join([str(i), 'PM' if pdiff < 0 else 'PP', playerstr])
                    pdifflist.extend([stri]*np.abs(pdiff))
                appender(' '.join(pdifflist))
            
            tilestart = game.tilethis
            tileend = tilestart + game.leftnum
            mountainview = game.mountain[tilestart:tileend]
            appender(''.join(['M '.join([IDX_TILER[i] for i, j in enumerate(mountainview) if j]), 'M']))

            appender(' '.join(['BET' for _ in range(game.bet + 1)]))
            appender(' '.join(['REP' for _ in range(game.repeat + 1)]))
            appender(' '.join(['DIR' for _ in range(game.direction + 1)]))
            appender(' '.join(['DORA' for _ in doraid]))
            appender('\n')

            recorddata = self.recorddata
            recorddata[0].append(','.join(recordstr))
            recorddata[1].append(action)

        return discardDecisions, chowDecisions, kongDecisions, \
            chowDos, pongDos, kongDos, ronDos, riichiDos, liujuDos, redfives

if __name__ == "__main__":
    uuid = '200715-1278a924-fa38-402f-a93c-9cf96eb409d4'
    recorder = RecorderText()
    recorder.runGame(uuid)
    print(recorder.game.roundid)
