import json
import os
from shutil import copyfile

import h5py
import numpy as np

# DEPRECATED in 10/22/2020 2:00
COLORS = {'m':0, 'p':9, 's':18, 'z':27}
MAX_ACTIONS = 5000

class Game(object):
    def __init__(self, jsonrecord=None, agents=None):
        super(Game, self).__init__()
        self.mountain = np.arange(4 * 34) # 牌山
        self.nonmiddle = np.array(
            [0, 8, 9, 17, 18, 26] + list(range(27, 34)), dtype='int'
        ) # 幺九
        self.nonmiddlechow = np.array([0, 6, 9, 15, 18, 24], dtype='int')
        self.doramap = lambda i: (i + 1) % 9 + i // 9 * 9 if i < 27 \
            else (i - 6) % (3 + (i < 31)) + 31 - (i < 31) * 4 # 宝牌指示
        self.bet = 0        # 立直棒
        self.repeat = 0     # 本场棒
        self.direction = 0  # 场风
        self.dealer = 0     # 亲家
        self.points = np.ones(4) * 25000 # 点数
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
        
        self.record = jsonrecord
        self.recordid = -1
        self.recorddata = h5py.File('tmp.h5', 'w')
        self.recorddata.create_dataset('statesCnt', \
            shape=(0, 2), maxshape=(MAX_ACTIONS, 2), dtype='i', chunks=True, compression="gzip")
        self.recorddata.create_dataset('states', \
            shape=(0, 4, 64, 34), maxshape=(MAX_ACTIONS, 4, 64, 34), dtype='f', chunks=True, compression="gzip")
        for item in ['discardDecisions', 'chowDecisions', 'kongDecisions']:
            self.recorddata.create_dataset(item, \
                shape=(0, 4, 34), maxshape=(MAX_ACTIONS, 4, 34), dtype='f', chunks=True, compression="gzip")
        for item in ['chowDos', 'pongDos', 'kongDos', 'ronDos', 'riichiDos', 'liujuDos', 'redfives']:
            self.recorddata.create_dataset(item, \
                shape=(0, 4), maxshape=(MAX_ACTIONS, 4), dtype='i', chunks=True, compression="gzip")
        self.players = agents
        if not self.record is None:
            self.players = self.recordPlayers
        self.newRound()
    
    def checkRound(self):
        assert not self.record is None
        assert self.record[self.recordid]['east'] == self.dealer
        assert self.record[self.recordid]['honba'] == self.repeat
        assert self.record[self.recordid]['kyoutaku'] == self.bet
        assert all(self.record[self.recordid]['point'] == self.points)
        assert self.record[self.recordid]['round'] == self.dealer + self.direction * 4
        
    def recordPlayers(self, states, masks):
        discardDecisions = np.zeros([4, 34])
        chowDecisions = np.zeros([4, 34])
        kongDecisions = np.zeros([4, 34])
        chowDos = np.zeros(4, dtype='int')
        pongDos = np.zeros(4, dtype='int')
        kongDos = np.zeros(4, dtype='int')
        ronDos = np.zeros(4, dtype='int')
        riichiDos = np.zeros(4, dtype='int')
        liujuDos = np.zeros(4, dtype='int')
        redfives = np.zeros(4, dtype='int')
        
        recorded = self.recorddata['states'].shape[0]
        self.recorddata['statesCnt'][-1, 1] += 1
        for item in ['states', 'discardDecisions', 'chowDecisions', 'kongDecisions', 
                     'chowDos', 'pongDos', 'kongDos', 'ronDos', 'riichiDos', 
                     'liujuDos', 'redfives']:
            self.recorddata[item].resize(recorded + 1, 0)
        recordthis = recorded - self.recorddata['statesCnt'][-1, 0]
        action = self.record[self.recordid]['action'][recordthis]
        actionType = action[0]
        if actionType == 'A': # 切
            player = int(action[1])
            discardDecisions[player, tileParser(action[2:4])] = 1
            # action[4] 1/0：摸切/手切，action[5] 1/0：立直/不立直
            riichiDos[player] = int(action[5])
            redfives[player] = action[2] == '0'
        elif actionType == 'B': # 摸
            actionnext = self.record[self.recordid]['action'][recordthis+1]
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
                    self.record[self.recordid]['action'].pop(recordthis+1)
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
            actionnext = self.record[self.recordid]['action'][recordthis+1]
            if actionnext[0] == 'X': # 双响
                ronDos[int(actionnext[2])] = 1
                actionnextnext = self.record[self.recordid]['action'][recordthis+2]
                if actionnextnext[0] == 'X': # 三响
                    ronDos[int(actionnextnext[2])] = 1
        elif actionType == 'Y': # 流局
            liujuDos[self.playerthis] = action[1] == '9'
        elif actionType == 'Z': # 结算
            pass
        else:
            raise Exception('Unknown action type '+actionType)
        self.recorddata['states'][-1] = states
        self.recorddata['discardDecisions'][-1] = discardDecisions
        self.recorddata['chowDecisions'][-1] = chowDecisions
        self.recorddata['kongDecisions'][-1] = kongDecisions
        self.recorddata['chowDos'][-1] = chowDos
        self.recorddata['pongDos'][-1] = pongDos
        self.recorddata['kongDos'][-1] = kongDos
        self.recorddata['ronDos'][-1] = ronDos
        self.recorddata['riichiDos'][-1] = riichiDos
        self.recorddata['liujuDos'][-1] = liujuDos
        self.recorddata['redfives'][-1] = redfives
        return discardDecisions, chowDecisions, kongDecisions, \
            chowDos, pongDos, kongDos, ronDos, riichiDos, liujuDos, redfives
    
    def newRound(self):
        self.recordid += 1
        if not self.record is None:
            self.mountain = mountainParser(self.record[self.recordid]['yama'])
        else:
            np.random.shuffle(self.mountain)
        self.doraid = [] # 宝牌索引
        self.dorainid = [] # 里宝牌索引
        self.hands = np.zeros([4, 4 * 34], dtype='int')  # 手牌
        self.shown = np.zeros([4, 4 * 34], dtype='int')  # 可见（副露或暗杠）
        self.unfixed = np.zeros([4, 4 * 34], dtype='int')# 可以打出
        self.dora = np.zeros([4, 4 * 34], dtype='int')   # 宝牌
        self.dorain = np.zeros([4, 4 * 34], dtype='int') # 里宝牌
        self.river = np.zeros([4, 4 * 34], dtype='int')  # 牌河
        # 发牌，标记宝牌
        self.doraid += [i * 34 + self.doramap(
            self.mountain[-5] % 34
            ) for i in range(4)]
        self.dorainid += [i * 34 + self.doramap(
            self.mountain[-6] % 34
            ) for i in range(4)]
        for i in range(4):
            self.hands[i-4+self.dealer][self.mountain[i*13:i*13+13]] = 1
        for i, hand in enumerate(self.hands):
            self.unfixed[i] += hand
            for idx in self.doraid:
                self.dora[i][idx] = hand[idx]
            for idx in self.dorainid:
                self.dorain[i][idx] = hand[idx]
        
        self.playerthis = self.dealer # 当前玩家
        self.tilethis = 52  # 当前摸牌
        self.doranum = 1    # 宝牌数
        self.leftnum = 70   # 余牌数

        self.grabkong = 0  # 抢杠
        self.ridgeview = 0 # 岭上开花
        self.liuju = 0     # 中途流局
        self.huangpai = 0  # 荒牌流局
        self.first = 1     # 第一巡
        self.riichi = np.zeros(4, dtype='int')  # 立直
        self.abrupt = np.zeros(4, dtype='int')  # 一发
        self.wriichi = np.zeros(4, dtype='int') # 两立直
        self.clear = np.ones(4, dtype='int')    # 门前清
        self.fritent = np.zeros(4, dtype='int') # 同巡振听
        self.fritens = np.zeros(4, dtype='int') # 舍张振听
        self.fritenl = np.zeros(4, dtype='int') # 立直振听
        self.roned = np.zeros(4, dtype='int')   # 和了点数
        self.liuman = np.ones(4, dtype='int')   # 流局满贯
        self.listen = np.zeros([4, 34], dtype='int')  # 听牌
        self.chowop = np.zeros([4, 34], dtype='int')  # 明顺
        self.pongop = np.zeros([4, 34], dtype='int')  # 明刻
        self.pongcls = np.zeros([4, 34], dtype='int') # 暗刻
        self.kongop = np.zeros([4, 34], dtype='int')  # 明杠
        self.kongcls = np.zeros([4, 34], dtype='int') # 暗杠
        self.recorddata['statesCnt'].resize(self.recorddata['statesCnt'].shape[0] + 1, 0)
        self.recorddata['statesCnt'][-1, 0] = self.recorddata['states'].shape[0]
        self.recorddata['statesCnt'][-1, 1] = 0
        
    def drawStep(self, idx, kongDecisions, kongDos, ronDos, liujuDos):
        """Draw a tile and related actions
        
        Args:
            idx (int): index of the drawn tile
            kongDecisions ((4, 34) float): which meld to kong
            kongDos ((4,) boolean): kong or not
            ronDos ((4,) boolean): ron or not
            liujuDos ((4,) boolean): nn or not
        
        Returns:
            boolean: next step, draw a tile if True, discard a tile if False 
        """
        if self.first and self.leftnum < 66:
            self.first = 0
        # 九种九牌
        if self.first and (self.hands[self.playerthis].reshape([4, 34]).sum(0)\
            [self.nonmiddle] > 0).sum() > 8 and liujuDos[self.playerthis]:
            self.liuju = 1
            return False
        # 自摸
        fanBase, fan, fu = self.ronAva(idx, self.playerthis, False)
        if fanBase > 0 and ronDos[self.playerthis]:
            pt1, pt2, _, _ = cntPts(fan, fu)
            if self.dealer == self.playerthis:
                for player in range(4):
                    if player == self.playerthis:
                        self.roned[player] += pt2 * 3 + self.bet * 1000 + self.repeat * 300
                    else:
                        self.roned[player] -= pt2 + self.repeat * 100
            else:
                for player in range(4):
                    if player == self.playerthis:
                        self.roned[player] += pt2 + pt1 * 2 + self.bet * 1000 + self.repeat * 300
                    elif player == self.dealer:
                        self.roned[player] -= pt2 + self.repeat * 100
                    else:
                        self.roned[player] -= pt1 + self.repeat * 100
            self.bet = 0
            return False
        # 杠
        if self.kongAva(idx, self.playerthis) and kongDos[self.playerthis]:
            # 若是加杠，需检查是否被抢杠，此处不考虑国士无双抢暗杠
            if self.kong(None, self.playerthis, kongDecisions[self.playerthis], None):
                self.grabkong = 1
                for position in range(3):
                    player = (self.playerthis + position + 1) % 4
                    fanBase, fan, fu = self.ronAva(idx, player, False)
                    if fanBase > 0 and ronDos[player] and \
                        not (self.fritenl[player] + self.fritens[player] + self.fritent[player]):
                        _, _, pt4, pt6 = cntPts(fan, fu)
                        pt = pt6 if self.dealer == player else pt4
                        self.roned[player] += pt + self.bet * 1000 + self.repeat * 300
                        self.roned[self.playerthis] -= pt + self.repeat * 300
                        self.bet = 0
                self.grabkong = 0
            return True
        return False
        
    def discardStep(self, idx, chowDecisions, chowDos, \
        pongDos, kongDos, ronDos, redfives):
        """Discard a tile and related actions
        
        Args:
            idx (int): index of the discarded tile
            chowDecisions ((4, 34) float): which meld to chow
            chowDos ((4,) boolean): chow or not
            pongDos ((4,) boolean): pong or not
            kongDos ((4,) boolean): kong or not
            ronDos ((4,) boolean): ron or not
            redfives ((4,) boolean): show red five or not
        
        Returns:
            boolean: next step, draw a tile if True, discard a tile if False 
        """
        # 检查是否放铳，由于立直棒头跳，需要按顺序检查
        for position in range(3):
            player = (self.playerthis + position + 1) % 4
            fanBase, fan, fu = self.ronAva(idx, player, False)
            if fanBase > 0 and ronDos[player] and \
                not (self.fritenl[player] + self.fritens[player] + self.fritent[player]):
                _, _, pt4, pt6 = cntPts(fan, fu)
                pt = pt6 if self.dealer == player else pt4
                self.roned[player] += pt + self.bet * 1000 + self.repeat * 300
                self.roned[self.playerthis] -= pt + self.repeat * 300
                self.bet = 0
            # 不和则同巡振听
            if fanBase and not ronDos[player]:
                self.fritent[player] = 1
        if any(self.roned):
            return True
        # 未放铳进入一发巡，则立直成立
        elif self.abrupt[self.playerthis]:
            self.bet += 1
            self.points[self.playerthis] -= 1000
        # 明杠
        for player in range(4):
            if (not (player == self.playerthis)) and self.kongAva(idx, player) and kongDos[player]:
                self.kong(idx, player, None, None)
                return True
        # 碰
        for player in range(4):
            if (not (player == self.playerthis)) and self.pongAva(idx, player) and pongDos[player]:
                self.pong(idx, player, None, redfives[player])
                return False
        # 吃
        self.playerthis = (self.playerthis + 1) % 4
        if self.chowAva(idx, None) and chowDos[self.playerthis]:
            self.chow(idx, self.playerthis, chowDecisions[self.playerthis], redfives[self.playerthis])
            return False
        # 四风连打，四杠散了
        if (self.first and self.river.sum(0).reshape([4, 34]).sum(0)[27:].max() == 4) or \
            (self.doranum == 5 and self.hands.sum(0).max() < 17):
            self.liuju = 1
        # 荒牌流局
        if not self.leftnum:
            self.huangpai = 1
        return True
        
    def runRound(self):
        """Run a round

        Returns:
            boolean: end of the game
        """
        nextStep = True
        for _ in range(MAX_ACTIONS):
            if self.liuju or self.huangpai or any(self.roned):
                break
            if nextStep:
                idx = self.draw()
                discardDecisions, _, kongDecisions, _, _, \
                    kongDos, ronDos, riichiDos, liujuDos, redfives = self.playersStep()
                nextStep = self.drawStep(
                    idx, kongDecisions, kongDos, ronDos, liujuDos
                )
                if nextStep: # 若仍是摸牌，需要重新决策
                    discardDecisions, _, kongDecisions, _, _, \
                        kongDos, ronDos, riichiDos, liujuDos, redfives = self.playersStep()
            else:
                idx = self.discard(
                    discardDecisions[self.playerthis], riichiDos[self.playerthis], redfives[self.playerthis]
                )
                discardDecisions, chowDecisions, _, chowDos, pongDos, \
                    kongDos, ronDos, riichiDos, _, redfives = self.playersStep()
                nextStep = self.discardStep(
                    idx, chowDecisions, chowDos, pongDos, kongDos, ronDos, redfives
                )
                if not nextStep: # 若仍是切牌，需要重新决策
                    discardDecisions, chowDecisions, _, chowDos, pongDos, \
                        kongDos, ronDos, riichiDos, _, redfives = self.playersStep()
        lastdealer = self.dealer
        lastdirection = self.direction
        if any(self.roned):
            self.bet = 0
            for player in range(4):
                self.points[player] += self.roned[player]
            # 亲家和则连庄，否则过庄
            if self.roned[self.dealer] > 0:
                self.repeat += 1
            else:
                self.repeat = 0
                self.dealer += 1
                if self.dealer == 4:
                    self.dealer = 0
                    self.direction += 1
        else:
            self.repeat += 1
            # 罚符
            listened = self.listen.sum(1) > 0
            if any(listened) and not all(listened) and self.huangpai: # 或not self.leftnum
                for player in range(4):
                    if listened[player]:
                        self.points[player] += int(3000 / listened.sum())
                    else:
                        self.points[player] -= int(3000 / (4 - listened.sum()))
            # 流局满贯
            for player in range(4):
                if self.liuman[player]:
                    if player == self.dealer:
                        for i in range(4):
                            if i == player:
                                self.points[i] += 12000
                            else:
                                self.points[i] -= 4000
                    else:
                        for i in range(4):
                            if i == player:
                                self.points[i] += 8000
                            elif i == self.dealer:
                                self.points[i] -= 4000
                            else:
                                self.points[i] -= 2000
            # 荒牌流局且亲家未听则过庄
            if not listened[self.dealer] and self.huangpai: # 或not self.leftnum
                self.dealer += 1
                if self.dealer == 4:
                    self.dealer = 0
                    self.direction += 1
        ko = self.points.min() < 0 # 击飞
        lastround = self.direction == 2 and self.points.max() > 30000 # 南四或西入
        northwin = self.points.argmax() == 3 and lastdirection == 1 and lastdealer == 3 # 南四亲一位
        finalround = self.direction == 3 # 无北入
        gameEnd = ko or lastround or northwin or finalround
        if gameEnd:
            self.points[self.points.argmax()] += self.bet * 1000
            assert all(
                [int(pt) for pt in self.record[self.recordid]['action'][-1][1:].split('|')] == \
                    self.points
                )
        else:
            self.newRound()
        return gameEnd
    
    def ronAva(self, idx, player, fast):
        """能不能和

        Args:
            idx (int): index of the tile
            player (int): index of the player
            fast (boolean): no details, only used when discard

        Returns:
            int: 有役番数，注意0为未听，-1为无役听牌
            int: 番数，有役番数加上宝牌
            int: 符数，对于满贯以上牌和无役听牌无意义
        """
        if fast: # 只是用来判断是否听牌
            player = self.playerthis
        cntall = self.hands[player].reshape([4, 34]).sum(0)
        tiles = np.where(cntall)[0]
        idxmod = idx % 34
        if (not self.playerthis == player) or fast:
            cntall[idxmod] += 1
        if any(self.kongcls[player]):
            assert all(cntall[self.kongcls[player]>0] > 3)
            cntall[self.kongcls[player]>0] -= 4
        if self.riichi[player]:
            cnt = cntall
        else:
            cnt = self.unfixed[player].reshape([4, 34]).sum(0)
            if not self.playerthis == player or fast:
                cnt[idxmod] += 1
        cnt = cnt.astype('int')
        assert np.sum(cnt)%3 == 2 # 若干面子加一将
        rontile = str(idxmod%9+1) + sorted(COLORS)[idxmod//9]
        # 国士无双/国士无双十三面
        thirteenorphans = len(tiles) == 13 and all(tiles == self.nonmiddle)
        # 七对子（也可能是两杯口，后续区分）
        sevenpairs = len(tiles) == 7 and all(cnt[tiles] == 2) and self.clear[player]
        # 面子手
        meldsall = cntMeldsAll(cnt)
        ronmelds = len(meldsall)
        if fast: # 只是用来判断是否听牌
            return ronmelds or thirteenorphans or sevenpairs
        # 国士无双/国士无双十三面
        if thirteenorphans:
            return 13, 13, 0
        # 未听
        if not (sevenpairs or ronmelds):
            return 0, 0, 0
        # 天和/地和/人和
        if (ronmelds or sevenpairs) and self.first:
            return 13, 13, 0
        # 绿一色
        if ronmelds and all([tile in [19, 20, 21, 23, 25, 32] for tile in tiles]):
            return 13, 13, 0
        # 清老头
        if all([tile in self.nonmiddle[:6] for tile in tiles]):
            return 13, 13, 0
        # 四杠子
        if (self.kongcls + self.kongop)[player].sum() == 4:
            return 13, 13, 0
        pongopall = (self.pongop + self.kongcls + self.kongop)[player]
        if ronmelds:
            # 大三元
            if all([str(i-26) * 3 + 'z' in meldsall[0] or \
                    pongopall[i] \
                        for i in range(31, 34)]):
                return 13, 13, 0
            # 小四喜/大四喜
            if all([str(i-26) * 3 + 'z' in meldsall[0] or str(i-26) * 2 + 'z' in meldsall[0] or \
                    pongopall[i] \
                        for i in range(27, 31)]):
                return 13, 13, 0
        # 立直，两立直，一发，抢杠，岭上开花，门清自摸，断幺九，海底摸月/河底捞鱼，混老头
        fan = self.riichi[player] + self.wriichi[player] + self.abrupt[player] + \
            self.grabkong + self.ridgeview + \
            (self.clear[player] and self.playerthis == player) + \
            (not any([tile in self.nonmiddle for tile in list(tiles)+[idxmod]])) + \
            (not self.leftnum) + \
            all([tile in self.nonmiddle for tile in list(tiles)+[idxmod]]) * 2
        if ronmelds:
            # 小三元
            if all([str(i-26) * 3 + 'z' in meldsall[0] or str(i-26) * 2 + 'z' in meldsall[0] or \
                    pongopall[i] \
                        for i in range(31, 34)]):
                fan += 2      
            # 自风，场风，役牌
            yiall = [(player - self.dealer) % 4, self.direction, 4, 5, 6]
            fan += sum([(str(yi + 1) * 3 + 'z' in meldsall[0]) or pongopall[yi+27] for yi in yiall])
        # 染手
        singlecolor = list(set([tile // 9 for tile in tiles]))
        numcolor = len(singlecolor)
        zincolor = 3 in singlecolor # 判断有没有字牌
        if numcolor == 1:
            if zincolor:
                # 字一色
                return 13, 13, 0
            else:
                # 九莲宝灯/纯正九莲宝灯
                tmp = tiles[0] // 9 * 9
                nine = cnt[tmp:tmp+9]
                # 纯正九莲宝灯听牌时各牌张数必为奇数（1或3）
                nine[nine%2==0] -= 1
                if all(nine == [3] + [1] * 7 + [3]) and self.clear[player] and not any(self.shown[player]):
                    return 13, 13, 0
                else:
                    # 清一色
                    fan += 5 + self.clear[player]
        # 混一色
        if numcolor == 2 and zincolor:
            fan += 2 + self.clear[player]
        # 宝牌/红宝牌，里宝牌
        fandora = self.dora[player].sum() + self.hands[player][106:133:9].sum() + \
            self.dorain[player].sum() * self.riichi[player]
        if not self.playerthis == player:
            fandora += int(idx in self.doraid) + int(idx in [106, 115, 124]) + \
                int(idx in self.dorainid) * self.riichi[player]
        # 七对子固定25符
        if sevenpairs and not ronmelds:
            return fan + 2, fan + 2 + fandora, 25
        # 三杠子
        fan += 2 * ((self.kongcls + self.kongop)[player].sum() == 3)
        # 高点原则
        fanmax = 0
        fumax = 0
        for melds in meldsall:
            fantmp = 0
            futmp = 0
            # 暗刻数
            npongcls = sum([
                    meld[0] == meld[1] and meld[1] == meld[2] and \
                        (player == self.playerthis or not rontile == meld[2:]) \
                    for meld in melds
                ])
            npongclsnonmiddle = sum([
                    meld[0] == meld[1] and meld[1] == meld[2] and \
                        (meld[0] == '1' or meld[0] == '9' or meld[-1] == 'z') and \
                        (player == self.playerthis or not rontile == meld[2:]) \
                    for meld in melds
                ])
            # 四暗刻/四暗刻单骑（暗杠也是暗刻）
            if self.kongcls[player].sum() + npongcls == 4:
                return 13, 13, 0
            # 三暗刻（暗杠也是暗刻）
            fantmp += 2 * (self.kongcls[player].sum() + npongcls == 3)
            # 三色同刻
            fantmp += 2 * any(
                [pongopall[i:27:9].sum() + \
                    sum([str(i+1)*3 == meld[:3] for meld in melds]) == 3 \
                for i in range(9)]
            )
            # 三色同顺
            fantmp += (1 + self.clear[player]) * any([
                (self.chowop[player][i:27:9] + \
                    np.array([str(111*i+123)+c in melds for c in sorted(COLORS)[:3]])).min() \
                for i in range(7)
            ])
            # 对对和
            fantmp += 2 * (pongopall.sum() + \
                    sum([meld[0] == meld[1] and meld[1] == meld[2] for meld in melds]) == 4)
            # 一杯口/两杯口
            fantmp += self.clear[player] * np.arange(3)[:\
                1+[melds.count(meld) for meld in list(set(melds))].count(2)\
                    ].sum()
            # 混全带幺九
            fantmp += (1 + self.clear[player]) * \
                (
                    all([meld[0] == '1' or meld[-2] == '9' or meld[-1] == 'z' for meld in melds]) and \
                    pongopall[self.nonmiddle].sum() == pongopall.sum() and \
                    self.chowop[player][self.nonmiddlechow].sum() == self.chowop[player].sum()
                )
            # 纯全带幺九（多一番）
            fantmp += all([meld[0] == '1' or meld[-2] == '9' for meld in melds]) and \
                    pongopall[self.nonmiddle[:6]].sum() == pongopall.sum()
            # 一气通贯
            isseq = [all(cntall[i*9:i*9+9]) for i in range(3)]
            if any(isseq):
                cnttmp = np.zeros(34, dtype='int')
                cnttmp += cntall
                seq = isseq.index(1)
                cnttmp[seq*9:seq*9+9] -= 1
                fantmp += (1 + self.clear[player]) * (len(cntMeldsAll(cnttmp)) > 0)
            # 算符
            futmp = any([str(yi + 1) * 2 + 'z' in melds for yi in yiall]) * 2 + \
                self.pongop[player].sum() * 2 + self.pongop[player][self.nonmiddle].sum() * 2 + \
                npongcls * 4 + npongclsnonmiddle * 4 + \
                self.kongop[player].sum() * 8 + self.kongop[player][self.nonmiddle].sum() * 8 + \
                self.kongcls[player].sum() * 16 + self.kongcls[player][self.nonmiddle].sum() * 16
            # 平和
            ping = self.clear[player] and not futmp and any([
                    # 两面
                    int(meld[0]) + 1 == int(meld[1]) and (
                        (meld[0] + meld[-1] == rontile and not meld[:3] == '789') or \
                        (meld[2] + meld[-1] == rontile and not meld[:3] == '123')
                        )
                    for meld in melds
                ])
            if ping:
                fantmp += 1
            # 尽量争取2符
            else:
                futmp += 2 * any([
                    # 坎张
                    (meld[1] + meld[-1] == rontile and int(meld[0]) + 1 == int(meld[1])) or \
                    # 边张
                    (meld[0] + meld[-1] == rontile and meld[:3] == '789') or \
                    (meld[2] + meld[-1] == rontile and meld[:3] == '123') or \
                    # 单骑
                    (meld[1] + meld[-1] == rontile and meld[0] == meld[1])
                    for meld in melds
                ])
            # 自摸2符，门前清荣和10符
            if self.playerthis == player:
                futmp += 2 * (not ping)
            elif self.clear[player]:
                futmp += 10
            # 一番20符作一番30符处理
            if fan + fantmp == 1 and not (futmp or fandora):
                futmp = 10
            futmp = 10 * int(np.ceil(futmp / 10))
            if fantmp > fanmax:
                fanmax = fantmp
                fumax = futmp
            elif fantmp == fanmax and futmp > fumax:
                fanmax = fantmp
                fumax = futmp   
        fan += fanmax
        # 无役听牌
        if (not fan) and ronmelds:
            return -1, -1, 0
        # 底符20符，加上宝牌/红宝牌，里宝牌
        return fan, fan + fandora, fumax + 20
    
    def pongAva(self, idx, player):
        """能不能碰

        Args:
            idx (int): index of the tile
            player (int): index of the player

        Returns:
            boolean: 能不能碰
        """
        return self.leftnum and self.unfixed[player][idx%34::34].sum() > 1  # 最后一张不能碰
    
    def chowAva(self, idx, player):
        """能不能吃

        Args:
            idx (int): index of the tile
            player (int): index of the player (dummy argument)

        Returns:
            boolean: 能不能吃
        """
        if not self.leftnum: # 最后一张不能吃
            return False
        idxmod = idx % 34
        if idxmod > 26: # 字牌不能吃
            return False
        i, j = idxmod // 9 * 9, idxmod % 9
        tmp = np.zeros(13, dtype='int')
        tmp[2:-2] += self.unfixed[self.playerthis].reshape([4, 34]).sum(0)[i:i+9]
        return (tmp[j] and tmp[j+1]) or (tmp[j+1] and tmp[j+3]) or \
            (tmp[j+3] and tmp[j+4])
        
    def kongAva(self, idx, player):
        """能不能杠

        Args:
            idx (int): index of the tile
            player (int): index of the player
        
        Returns:
            boolean: 能不能杠
        """
        flag = 0
        idxmod = idx % 34
        if player == self.playerthis: # 加杠或暗杠
            if self.riichi[player]: # 立直后暗刻才能暗杠
                flag += self.pongcls[player][idxmod]
            else:
                unfixedcnt = self.unfixed[player].reshape([4, 34]).sum(0)
                flag = unfixedcnt.max() == 4 or \
                    any(np.logical_and(self.pongop[player], unfixedcnt))
        else: # 明杠
            flag = self.unfixed[player].reshape([4, 34]).sum(0)[idxmod] == 3
        return self.leftnum and flag  # 最后一张不能杠
    
    def draw(self):
        """Draw a tile

        Returns:
            int: index of the tile
        """
        if self.ridgeview:
            idx = self.mountain[-self.doranum]
            self.hands[self.playerthis][idx] = 1
            self.unfixed[self.playerthis][idx] = 1
            self.dora[self.playerthis][idx] = idx in self.doraid
            self.dorain[self.playerthis][idx] = idx in self.dorainid
            self.doranum += 1
            assert self.doranum < 6
            self.doraid += [i * 34 + self.doramap(
                self.mountain[-3 - self.doranum * 2] % 34
                ) for i in range(4)]
            self.dorainid += [i * 34 + self.doramap(
                self.mountain[-4 - self.doranum * 2] % 34
                ) for i in range(4)]
            for i, hand in enumerate(self.hands):
                for j in self.doraid[-4:]:
                    self.dora[i][j] = hand[j]
                for j in self.dorainid[-4:]:
                    self.dorain[i][j] = hand[j]
        else:
            idx = self.mountain[self.tilethis]
            self.hands[self.playerthis][idx] = 1
            self.unfixed[self.playerthis][idx] = 1
            self.dora[self.playerthis][idx] = idx in self.doraid
            self.dorain[self.playerthis][idx] = idx in self.dorainid
            self.tilethis += 1
        self.leftnum -= 1
        return idx
    
    def discard(self, decision, riichiDo, redfive):
        """Discard a tile

        Args:
            decision ((34,) float): which tile to discard
            riichiDo (boolean): riichi or not
            redfive (boolean): discard red five or not

        Returns:
            int: index of the tile
        """
        self.ridgeview = 0
        idxmod = np.argmax(decision * (self.unfixed[self.playerthis].reshape([4, 34]).sum(0) > 0))
        if not idxmod in self.nonmiddle:
            self.liuman[self.playerthis] = 0
        rng = list(range(idxmod, 4 * 34, 34))
        if redfive:
            rng.reverse()
        flag = 0
        for idx in rng:
            if self.unfixed[self.playerthis][idx]:
                self.river[self.playerthis][idx] = 1
                self.hands[self.playerthis][idx] = 0
                self.unfixed[self.playerthis][idx] = 0
                self.dora[self.playerthis][idx] = 0
                self.dorain[self.playerthis][idx] = 0
                flag = 1
                break
        assert flag
        self.listen[self.playerthis] *= 0
        for i in range(34):
            if self.ronAva(i, self.playerthis, True):
                self.listen[self.playerthis, i] = 1
        if any(self.listen[self.playerthis]):
            self.fritens[self.playerthis] = 0
            for i in range(4 * 34):
                if self.river[self.playerthis][i] and self.listen[self.playerthis, i%34]:
                    self.fritens[self.playerthis] = 1
        if self.abrupt[self.playerthis]:
            self.abrupt[self.playerthis] = 0
        if any(self.listen[self.playerthis]) and riichiDo and \
            self.points[self.playerthis] > 1000 and self.clear[self.playerthis] and \
            not self.riichi[self.playerthis]:
            self.riichi[self.playerthis] = 1
            self.abrupt[self.playerthis] = 1
            self.wriichi[self.playerthis] = self.first
            self.unfixed[self.playerthis] *= 0
            self.pongclsChecker()
        if self.riichi[self.playerthis] and self.fritens[self.playerthis]:
            self.fritenl[self.playerthis] = 1
        self.fritent[self.playerthis] = 0
        return idx
    
    def pong(self, idx, player, decision, redfive):
        """Pong a tile

        Args:
            idx (int): index of the tile
            player (int): index of the player
            decision ((34,) float): which meld to pong (dummy argument)
            redfive (boolean): show red five or not
        
        Returns:
            boolean: if it is errorless
        """
        self.abrupt *= 0
        self.first = 0
        self.liuman[self.playerthis] = 0
        self.playerthis = player
        self.clear[player] = 0
        self.shown[player][idx] = 1
        self.hands[player][idx] = 1
        self.dora[player][idx] = idx in self.doraid
        self.dorain[player][idx] = idx in self.dorainid
        idxmod = idx % 34
        self.pongop[player][idxmod] = 1
        rng = list(range(idxmod, 4 * 34, 34))
        if redfive:
            rng.reverse()
        flag = 0
        for i in rng:
            if self.unfixed[player][i]:
                self.shown[player][i] = 1
                self.unfixed[player][i] = 0
                flag += 1
                if flag == 2:
                    break
        assert flag == 2
        return flag == 2
    
    def chow(self, idx, player, decision, redfive):
        """Chow a tile

        Args:
            idx (int): index of the tile
            player (int): index of the player (dummy argument)
            decision ((34,) float): which meld to chow
            redfive (boolean): show red five or not
        
        Returns:
            boolean: if it is errorless
        """
        self.abrupt *= 0
        self.first = 0
        assert player == self.playerthis
        self.liuman[player-1] = 0
        self.clear[player] = 0
        self.shown[player][idx] = 1
        self.hands[player][idx] = 1
        self.dora[player][idx] = idx in self.doraid
        self.dorain[player][idx] = idx in self.dorainid
        idxmod = idx % 34
        i, j = idxmod // 9 * 9, idxmod % 9
        tmp = np.zeros(13)
        tmp[2:-2] += (decision * (self.unfixed[player].reshape([4, 34]).sum(0) > 0))[i:i+9]
        if tmp[j] > tmp[j+3] and tmp[j] + tmp[j+1] > tmp[j+3] + tmp[j+4]:
            idx0, idx1 = idxmod - 2, idxmod - 1
            self.chowop[player][idxmod-2] += 1
        elif tmp[j+1] > tmp[j+4]:
            idx0, idx1 = idxmod - 1, idxmod + 1
            self.chowop[player][idxmod-1] += 1
        else:
            idx0, idx1 = idxmod + 1, idxmod + 2
            self.chowop[player][idxmod] += 1
        rng0 = list(range(idx0, 4 * 34, 34))
        if redfive:
            rng0.reverse()
        flag0 = 0
        for i in rng0:
            if self.unfixed[player][i]:
                self.shown[player][i] = 1
                self.unfixed[player][i] = 0
                flag0 = 1
                break
        assert flag0
        rng1 = list(range(idx1, 4 * 34, 34))
        if redfive:
            rng1.reverse()
        flag1 = 0
        for i in rng1:
            if self.unfixed[player][i]:
                self.shown[player][i] = 1
                self.unfixed[player][i] = 0
                flag1 = 1
                break
        assert flag1
        return flag0 and flag1
        
    def kong(self, idx, player, decision, redfive):
        """Kong a tile
        
        Args:
            idx (int): index of the tile
            player (int): index of the player 
            decision ((34,) float): which meld to kong
            redfive (boolean): show red five or not (dummy argument)

        Returns:
            boolean: if it is add kong (which can be grabbed)
        """
        self.abrupt *= 0
        self.first = 0
        self.ridgeview = 1 # 下一张从岭上摸牌
        flag = 0
        # 加杠或暗杠
        if player == self.playerthis:
            if self.riichi[player]:
                pongclsmelds = self.pongcls[player]
            else:
                pongclsmelds = self.unfixed[player].reshape([4, 34]).sum(0) == 4
            idxmod = np.argmax(decision * (self.pongop[player] + pongclsmelds))
            flag += self.pongop[player][idxmod]
            if self.pongop[player][idxmod]:
                self.pongop[player][idxmod] = 0
                self.kongop[player][idxmod] = 1
            else:
                self.pongcls[player][idxmod] = 0
                self.kongcls[player][idxmod] = 1
        # 明杠
        else:
            self.liuman[self.playerthis] = 0
            self.playerthis = player
            self.clear[player] = 0
            self.shown[player][idx] = 1
            self.hands[player][idx] = 1
            self.dora[player][idx] = idx in self.doraid
            self.dorain[player][idx] = idx in self.dorainid
            idxmod = idx % 34
            self.pongcls[player][idxmod] = 0
            self.kongop[player][idxmod] = 1
        self.shown[player][idxmod::34] = 1
        self.unfixed[player][idxmod::34] = 0
        return flag
    
    def pongclsChecker(self):
        """Check the number of definite pong close this player has
        """
        # 应当在立直时确定所有的暗刻以防可能的暗杠改变听牌型
        player = self.playerthis
        cnt = self.hands[player].reshape([4, 34]).sum(0)
        if any(self.kongcls[player]):
            assert all(cnt[self.kongcls[player]>0] > 3)
            cnt[self.kongcls[player]>0] -= 4
        meldsall = []
        for i in np.where(self.listen[player])[0]:
            cnttmp = np.zeros(34, dtype='int')
            cnttmp[i] = 1
            cnttmp += cnt
            meldsall += cntMeldsAll(cnttmp)
        if len(meldsall):
            # 只有所有听牌型下和牌后均为暗刻才是真的暗刻
            pongclsmelds = []
            for meld in meldsall[0]:
                if len(meld) == 3:
                    continue
                for melds in meldsall:
                    if meld[0] == meld[1] and meld[1] == meld[2] and meld in melds:
                        pongclsmelds.append(meld)
            for meld in pongclsmelds:
                self.pongcls[player][int(meld[0])+COLORS[meld[-1]]-1] = 1
    
    def playersStep(self):
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
        # 记录当前牌局状态
        state = np.zeros([64, 34])
        state[0] += self.bet / 2
        state[1] += self.repeat / 2
        state[2] += self.direction
        state[3, np.array(self.doraid)[::4]] = 1
        mountainview = np.zeros([4, 34])
        for i in range(4):
            for j in self.mountain[self.tilethis+i:self.tilethis+i+self.leftnum]:
                mountainview[i, j%34] += 1
        for player in range(4):
            state[4+player] += self.points[player] / 8000
            state[8+player] += self.river[player][self.doraid].sum()
            state[12+player] += self.shown[player][self.doraid].sum()
            state[16+player] += self.clear[player]
            state[20+player] += self.riichi[player]
            state[24+player] += self.dealer == player
            state[28+player] += self.river[player].reshape([4, 34]).sum(0)
            state[32+player] += self.shown[player].reshape([4, 34]).sum(0)
            # partial observable
            state[36+player] += self.hands[player][self.doraid].sum()
            state[40+player] += self.hands[player].reshape([4, 34]).sum(0)
            state[44+player] += self.unfixed[player].reshape([4, 34]).sum(0)
            state[48+player] += mountainview[player]
            state[52+player] += mountainview[player-1]
            state[56+player] += mountainview[player-2]
            state[60+player] += mountainview[player-3]
        # 四人分别记录状态
        states = np.zeros([4, 64, 34])
        for player in range(4):
            states[player] += state
            states[player, 4:8] = np.tanh(
                states[player, 4:8] - states[player, 4+player]
            )
        discardDecisions, chowDecisions, kongDecisions, chowDos, pongDos, kongDos, \
            ronDos, riichiDos, liujuDos, redfives = self.players(states, self.masks)
        return discardDecisions, chowDecisions, kongDecisions, \
            chowDos, pongDos, kongDos, ronDos, riichiDos, liujuDos, redfives
        
def cntMeldsAll(cnt):
    melds3 = np.zeros(4)
    melds2 = np.zeros(4)
    meldsi = []
    isomers = np.zeros(4)
    for i, _ in enumerate(reversed(sorted(COLORS))):
        melds3[i], melds2[i], melds, isomers[i] = cntMelds(cnt[27-i*9:36-i*9])
        if np.isnan(melds3[i]):
            return []
        meldsi.append(melds)
    if not melds3.sum() == np.sum(cnt)//3 and melds2.sum() == 1:
        return []
    meldsall = []
    for meldsz in meldsi[0]:
        for meldss in meldsi[1]:
            for meldsp in meldsi[2]:
                for meldsm in meldsi[3]:
                    meldsall.append(
                        [meldz + 'z' for meldz in meldsz] + \
                        [melds + 's' for melds in meldss] + \
                        [meldp + 'p' for meldp in meldsp] + \
                        [meldm + 'm' for meldm in meldsm]
                    )
    assert len(meldsall) == isomers[0] * isomers[1] * isomers[2] * isomers[3]
    return meldsall

def cntMelds(cnt):
    if not (np.sum(cnt)%3 == 1):
        # 字牌
        if len(cnt) == 7:
            melds = []
            cntcnt = np.zeros(5) # 某种字牌可能有0~4张
            for tile, num in enumerate(cnt):
                cntcnt[num] += 1
                if num:
                    melds.append(str(tile+1) * num)
            if not (cntcnt[1] or cntcnt[4] or cntcnt[2] > 1):
                return cntcnt[3], cntcnt[2], [melds], 1
        elif len(cnt) == 9:
            childl = np.zeros(9, dtype='int')
            childr = np.zeros(9, dtype='int')
            l3 = np.nan
            r3 = np.nan
            # disconnect
            for i in range(1, 8):
                if cnt[i-1] and (not cnt[i]) and np.sum(cnt[i+1:]):
                    childl[:i] += cnt[:i]
                    childr[i:] += cnt[i:]
                    break
            if any(childl):
                l3, l2, lm, li = cntMelds(childl)
                r3, r2, rm, ri = cntMelds(childr)
                lrm = []
                for lmi in lm:
                    for rmi in rm:
                        lrm.append(lmi + rmi)
                return l3 + r3, l2 + r2, lrm, li * ri
            # leaf
            cntsum = np.sum(cnt)
            cntmax = np.max(cnt)
            cntpos = np.argmax(cnt)
            if cntsum == 0:
                return 0, 0, [[]], 1
            if cntsum == 2 and cntmax == 2:
                return 0, 1, [[str(cntpos+1) * 2]], 1
            if cntsum == 3:
                if cntmax == 3:
                    return 1, 0, [[str(cntpos+1)*3]], 1
                if cntmax == 1:
                    return 1, 0, [[str(cntpos+1)+str(cntpos+2)+str(cntpos+3)]], 1
            # decomposition
            i = list(cnt > 0).index(True)
            if i > 6: # only 8 or 9, can not form meld
                melds = []
                cntcnt = np.zeros(5)
                for tile, num in enumerate(cnt):
                    cntcnt[num] += 1
                    if num:
                        melds.append(str(tile+1) * num)
                if not (cntcnt[1] or cntcnt[4] or cntcnt[2] > 1):
                    return cntcnt[3], cntcnt[2], [melds], 1
            elif cnt[i] == 1 or cnt[i] == 4: # 一定有至少一个顺子
                if cnt[i+1] and cnt[i+2]:
                    # we can use childl here because if any(childl) has returned
                    childl += cnt
                    childl[i:i+3] -= 1
                    l3, l2, lm, li = cntMelds(childl)
                    if not np.isnan(l3):
                        lm = [lmi + [str(i+1)+str(i+2)+str(i+3)] for lmi in lm]
                        return l3 + 1, l2, lm, li
            elif cnt[i] == 2:
                # 做将或有一杯口形状
                childl += cnt
                childl[i] -= 2
                l3, l2, lm, li = cntMelds(childl)
                if cnt[i+1] > 1 and cnt[i+2] > 1: 
                    childr += cnt
                    childr[i:i+3] -= 2
                    r3, r2, rm, ri = cntMelds(childr)
                if not np.isnan(l3):
                    lm = [lmi + [str(i+1)*2] for lmi in lm]
                    l2 += 1
                    if not np.isnan(r3):
                        if l3 == r3 + 2 and l2 == r2:
                            rm = [rmi + [str(i+1)+str(i+2)+str(i+3)]*2 for rmi in rm]
                            lm += rm
                            li += ri
                    return l3, l2, lm, li
                elif not np.isnan(r3):
                    rm = [rmi + [str(i+1)+str(i+2)+str(i+3)]*2 for rmi in rm]
                    r3 += 2
                    return r3, r2, rm, ri
            else: # 做刻或做将或有三杯口形状
                # 虽然三杯口是三暗刻，但是在最本格的规则里需要区分，因为三暗刻未必是三杯口
                childl += cnt
                childl[i] -= 3
                l3, l2, lm, li = cntMelds(childl)
                if cnt[i+1] and cnt[i+2]: # 做将或三杯口形状一定有至少一个顺子
                    childr += cnt
                    childr[i:i+3] -= 1
                    r3, r2, rm, ri = cntMelds(childr)
                if not np.isnan(l3):
                    lm = [lmi + [str(i+1)*3] for lmi in lm]
                    l3 += 1
                    if not np.isnan(r3):
                        rm = [rmi + [str(i+1)+str(i+2)+str(i+3)] for rmi in rm]
                        lm += rm
                        li += ri
                    return l3, l2, lm, li
                elif not np.isnan(r3):
                    rm = [rmi + [str(i+1)+str(i+2)+str(i+3)] for rmi in rm]
                    r3 += 1
                    return r3, r2, rm, ri
    return np.nan, np.nan, [[]], 0

def cntPts(fan, fu):
    pt = np.array([1, 2, 4, 6])
    if not ((fan == 4 and fu > 30) or (fan == 3 and fu > 60) or fan > 4):
        pt = np.ceil(fu / 100 * pt * (2 ** (fan + 2))) * 100
    elif fan < 6:
        pt *= 2000
    elif fan < 8:
        pt *= 3000
    elif fan < 11:
        pt *= 4000
    elif fan < 13:
        pt *= 6000
    else:
        pt *= 8000
    return pt

def mountainParser(yama):
    cnt = np.zeros([4, 34], dtype='int')
    mountain = np.zeros(4 * 34, dtype='int')
    for i in range(4 * 34):
        n = int(yama[i*2])
        c = COLORS[yama[i*2+1]]
        if n:
            cntcnt = cnt[:3, n+c-1].sum()
            cnt[cntcnt, n+c-1] = 1
            mountain[i] = cntcnt * 34 + n + c - 1
        else:
            cnt[3, 4+c] = 1
            mountain[i] = 3 * 34 + 4 + c
    return mountain

def tileParser(tile):
    n = int(tile[0])
    c = COLORS[tile[1]]
    if n:
        idxmod = n + c - 1
    else:
        idxmod = 4 + c
    return idxmod

if __name__ == "__main__":
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
        for _ in range(MAX_ACTIONS):
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
