import numpy as np

class Game(object):
    def __init__(self):
        super(Game, self).__init__()
        self.mountain = np.arange(4 * 34) # 牌山
        self.nonmiddle = np.array(
            [0, 8, 9, 17, 18, 26] + list(range(27, 34)), dtype='int'
        ) # 幺九
        self.nonmiddlechow = np.array([0, 6, 9, 15, 18, 24]), dtype='int')
        self.doramap = lambda i: (i + 1) % 9 + i // 9 * 9 if i < 27 \
            else (i - 6) % (3 + (i < 31)) + 31 - (i < 31) * 4 # 宝牌指示
        self.bet = 0        # 立直棒
        self.repeat = 0     # 本场棒
        self.direction = 0  # 场风
        self.dealer = 0     # 亲家
        self.points = np.ones(4) * 25000 # 点数
        self.players = None # 玩家指令
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
        self.newRound()
        
    def newRound(self):
        np.random.shuffle(self.mountain)
        self.doraid = [106, 115, 124] # 宝牌索引
        self.dorainid = [] # 里宝牌索引
        self.hands = np.zeros([4, 4 * 34], dtype='int')  # 手牌
        self.shown = np.zeros([4, 4 * 34], dtype='int')  # 可见（副露或暗杠）
        self.unfixed = np.zeros([4, 4 * 34], dtype='int')# 可以打出
        self.dora = np.zeros([4, 4 * 34], dtype='int')   # 宝牌
        self.dorain = np.zeros([4, 4 * 34], dtype='int') # 里宝牌
        self.river = np.zeros([4, 4 * 34], dtype='int')  # 牌河
        # 发牌，标记宝牌
        for i in range(4):
            self.hands[i][self.mountain[i*13:i*13+13]] = 1
            self.unfixed[i] = self.hands[i]
        for i, hand in enumerate(self.hands):
            for idx in self.doraid:
                self.dora[i][idx] = hand[idx]
            for idx in self.dorainid:
                self.dorain[i][idx] = hand[idx]
        
        self.playerthis = 0 # 当前玩家
        self.tilethis = 52  # 当前摸牌
        self.doranum = 1    # 宝牌数
        self.leftnum = 69   # 余牌数

        self.grabkong = 0  # 抢杠
        self.ridgeview = 0 # 岭上开花
        self.liuju = 0     # 流局
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
        
    def drawStep(self, kongDecisions, kongDos, ronDos, liujuDos):
        """Draw a tile and related actions
        
        Args:
            kongDecisions ((4, 34) float): which meld to kong
            kongDos ((4,) boolean): kong or not
            ronDos ((4,) boolean): ron or not
            liujuDos ((4,) boolean): nn or not
        
        Returns:
            boolean: next step, draw a tile if True, discard a tile if False 
        """
        if self.first and self.leftnum < 66:
            self.first = 0
        idx = self.draw()
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
        if self.kongAva(None, self.playerthis) and kongDos[self.playerthis]:
            self.ridgeview = 1 # 下一张从岭上摸牌
            # 若是加杠，需检查是否被抢杠，此处不考虑国士无双抢暗杠
            if self.kong(None, self.playerthis, kongDecisions[self.playerthis], None):
                self.grabkong = 1
                for position in range(3):
                    player = (self.playerthis + position + 1) % 4
                    fanBase, fan, fu = self.ronAva(idx, player, False)
                    if fanBase > 0 and ronDos[player] and \
                        not (self.fritenl[player] + self.fritens[player] + self.fritent[player]):
                        pt = int(np.ceil((int(self.dealer == player) * 2 + 4) * \
                            int(np.ceil(fu / 10)) / 10 * (2 ** (fan + 2)))) * 100
                        self.roned[player] += pt + self.bet * 1000 + self.repeat * 300
                        self.roned[self.playerthis] -= pt + self.bet * 1000 + self.repeat * 300
                        self.bet = 0
                self.grabkong = 0
            return True
        return False
        
    def discardStep(self, discardDecisions, chowDecisions, chowDos, \
        pongDos, kongDos, ronDos, riichiDos, redfives):
        """Discard a tile and related actions
        
        Args:
            discardDecisions ((4, 34) float): which tile to discard
            chowDecisions ((4, 34) float): which meld to chow
            chowDos ((4,) boolean): chow or not
            pongDos ((4,) boolean): pong or not
            kongDos ((4,) boolean): kong or not
            ronDos ((4,) boolean): ron or not
            riichiDos ((4,) boolean): riichi or not 
            redfives ((4,) boolean): show red five or not
        
        Returns:
            boolean: next step, draw a tile if True, discard a tile if False 
        """
        idx = self.discard(discardDecisions[self.playerthis], riichiDos[self.playerthis])
        # 检查是否放铳，由于立直棒头跳，需要按顺序检查
        for position in range(3):
            player = (self.playerthis + position + 1) % 4
            fanBase, fan, fu = self.ronAva(idx, player, False)
            if fanBase > 0 and ronDos[player] and \
                not (self.fritenl[player] + self.fritens[player] + self.fritent[player]):
                pt = int(np.ceil((int(self.dealer == player) * 2 + 4) * \
                    int(np.ceil(fu / 10)) / 10 * (2 ** (fan + 2)))) * 100
                self.roned[player] += pt + self.bet * 1000 + self.repeat * 300
                self.roned[self.playerthis] -= pt + self.bet * 1000 + self.repeat * 300
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
                return False
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
        # 四风连打，四杠散了，荒牌流局
        if (self.first and self.river.sum(0).reshape([4, 34]).sum(0)[27:].max() == 4) or \
            (self.doranum == 5 and self.hands.sum(0).max() < 17) or \
                (not self.leftnum):
            self.liuju = 1
        return True
        
    def runRound(self):
        """Run a round

        Returns:
            boolean: end of the game
        """
        nextStep = True
        while not (self.liuju or any(self.roned)):
            discardDecisions, chowDecisions, kongDecisions, chowDos, pongDos, \
                kongDos, ronDos, riichiDos, liujuDos, redfives = self.playersStep()
            if nextStep:
                nextStep = self.drawStep(
                    kongDecisions, kongDos, ronDos, liujuDos
                )
            else:
                nextStep = self.discardStep(
                    discardDecisions, chowDecisions, \
                    chowDos, pongDos, riichiDos, redfives
                )
        if any(self.roned):
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
            repeat += 1
            # 罚符
            listened = self.listen.sum(1) > 0
            if any(listened) and not self.leftnum:
                for player in range(4):
                    if any(self.listen[player]):
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
            # 亲家未听则过庄
            if not listened[self.dealer]:
                self.dealer += 1
                if self.dealer == 4:
                    self.dealer = 0
                    self.direction += 1
        ko = self.points.min() < 0 # 击飞
        lastround = self.direction == 2 and self.points.max() > 30000 # 南四或西入
        northwin = self.points.argmax() == 3 and self.direction == 1 and self.dealer == 3 # 南四亲一位
        finalround = self.direction == 3 # 无北入
        gameEnd = ko or lastround or northwin or finalround
        if gameEnd:
            self.points[self.points.argmax()] += self.bet * 1000
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
        idx %= 34
        cntall = self.hands[player].reshape([4, 34]).sum(0)
        if not self.playerthis == player or fast:
            cntall[idx] += 1
        assert all(cntall[self.kongcls[player]] == 4)
        cntall[self.kongcls[player]] = 0
        if self.riichi[player]:
            cnt = cntall
        else:
            cnt = self.unfixed[player].reshape([4, 34]).sum(0)
            if not self.playerthis == player or fast:
                cnt[idx] += 1
        assert np.sum(cnt)%3 == 2 # 若干面子加一将
        rontile = str(idx%9+1) + ['m', 'p', 's', 'z'][idx // 9]
        tiles = np.where(cnt)[0]
        # 国士无双/国士无双十三面
        thirteenorphans = len(tiles) == 13 and all(tiles == self.nonmiddle)
        # 七对子（也可能是两杯口，后续区分）
        sevenpairs = len(tiles) == 7 and all(cnt == 2) and self.clear[player]
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
        if self.kongcls[player] + self.kongop[player] == 4:
            return 13, 13, 0
        pongopall = (self.pongop + self.kongcls + self.kongop)[player]
        # 大三元
        if all([str(i - 31) * 3 + 'z' in meldsall[0] or \
                    pongopall[i] \
                        for i in range(31, 34)]):
            return 13, 13, 0
        # 小四喜/大四喜
        if all([str(i - 27) * 3 + 'z' in meldsall[0] or str(i - 27) * 2 + 'z' in melds or \
                    pongopall[i] \
                        for i in range(27, 31)]):
            return 13, 13, 0
        # 立直，两立直，一发，抢杠，岭上开花，门清自摸，断幺九，海底摸月/河底捞鱼，混老头
        fan = self.riichi[player] + self.wriichi[player] + self.abrupt[player] + \
            self.grabkong + self.ridgeview + \
            (self.clear[player] and self.playerthis == player) + \
            (not any([tile in self.nonmiddle for tile in tiles])) + \
            (not self.leftnum) + \
            all([tile in self.nonmiddle for tile in tiles]) * 2
        # 小三元
        if all([str(i - 31) * 3 + 'z' in meldsall[0] or str(i - 31) * 2 + 'z' in meldsall[0] or \
                    pongopall[i] \
                        for i in range(31, 34)]):
            fan += 2      
        # 自风，场风，役牌
        yiall = [str((player - self.dealer) % 4 + 1), str(self.direction + 1), 5, 6, 7]
        fan += sum([yi * 3 + 'z' in meldsall[0] for yi in yiall])
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
        fandora = self.dora[player].sum() + self.dorain[player].sum() * self.riichi[player]
        # 七对子固定25符
        if sevenpairs and not ronmelds:
            return fan, fan + fandora, 25
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
                [self.chowop[player][i:27:9].sum() + \
                    sum([str(i+1)+str(i+2)+str(i+3) == meld[:3] for meld in melds]) == 3 \
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
            futmp = any([yi * 2 + 'z' in melds for yi in yiall]) * 2 + \
                self.pongop[player].sum() * 2 + self.pongop[player][self.nonmiddle].sum() * 2 + \
                npongcls * 4 + npongclsnonmiddle * 4 + \
                self.kongop[player].sum() * 8 + self.kongop[player][self.nonmiddle].sum() * 8 + \
                self.kongcls[player].sum() * 16 + self.kongcls[player][self.nonmiddle].sum() * 16
            # 平和
            if self.clear[player] and not futmp and any([
                    # 两面
                    (meld[0] + meld[-1] == rontile and not meld[:3] == '789') or \
                    (meld[2] + meld[-1] == rontile and not meld[:3] == '123')
                    for meld in melds
                ]):
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
                futmp += 2
            elif self.clear[player]:
                futmp += 10
            # 一番20符作一番30符处理
            if fan + fantmp == 1 and not (futmp or fandora):
                futmp = 10
            futmp = 10 * int(np.ceil(futmp / 10))
            if fantmp > fanmax:
                fanmax = fantmp
                fumax = futmp
            elif futmp > fumax:
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
        return self.leftnum and self.unfixed[player][idx%34::34].sum() > 1
    
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
        idx %= 34
        if idx > 26: # 字牌不能吃
            return False
        i, j = idx // 9 * 9, idx % 9
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
        if player == self.playerthis: # 加杠或暗杠
            if self.riichi[player]: # 立直后暗刻才能暗杠
                flag += self.pongcls[player][self.argmax(self.unfixed[player])%34]
            else:
                unfixedcnt = self.unfixed[player].reshape([4, 34]).sum(0)
                flag = unfixedcnt.max() == 4 or \
                    any(np.logical_and(self.pongop[player], unfixedcnt))
        else: # 明杠
            flag = self.unfixed[player].reshape([4, 34]).sum(0)[idx%34] == 3
        return self.leftnum and flag
    
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
                self.mountain[-4 - self.doranum * 2] % 34
                ) for i in range(4)]
            self.dorainid += [i * 34 + self.doramap(
                self.mountain[-3 - self.doranum * 2] % 34
                ) for i in range(4)]
            for i, hand in enumerate(self.hands):
                for idx in self.doraid[-4:]:
                    self.dora[i][idx] = hand[idx]
                for idx in self.dorainid[-4:]:
                    self.dorain[i][idx] = hand[idx]
        else:
            idx = self.mountain[self.tilethis]
            self.hands[self.playerthis][idx] = 1
            self.unfixed[self.playerthis][idx] = 1
            self.dora[self.playerthis][idx] = idx in self.doraid
            self.dorain[self.playerthis][idx] = idx in self.dorainid
            self.tilethis += 1
        self.leftnum -= 1
        return idx
    
    def discard(self, decision, riichiDo):
        """Discard a tile

        Args:
            decision ((34,) float): which tile to discard
            riichiDo (boolean): riichi or not

        Returns:
            int: index of the tile
        """
        self.ridgeview = 0
        idx = np.argmax(decision * (self.unfixed[self.playerthis].reshape([4, 34]).sum(0) > 0))
        if not idx in self.nonmiddle:
            self.liuman[self.playerthis] = 0
        flag = 0
        for i in range(idx, 4 * 34, 34):
            if self.unfixed[self.playerthis][i]:
                self.river[self.playerthis][i] = 1
                self.hands[self.playerthis][i] = 0
                self.unfixed[self.playerthis][i] = 0
                self.dora[self.playerthis][i] = 0
                self.dorain[self.playerthis][i] = 0
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
        idx %= 34
        self.pongop[player][idx] = 1
        rng = list(range(idx, 4 * 34, 34))
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
        idx %= 34
        i, j = idx // 9 * 9, idx % 9
        tmp = np.zeros(13)
        tmp[2:-2] += (decision * (self.unfixed[player].reshape([4, 34]).sum(0) > 0))[i:i+9]
        if tmp[j] > tmp[j+3] and tmp[j] + tmp[j+1] > tmp[j+3] + tmp[j+4]:
            idx0, idx1 = idx - 2, idx - 1
            self.chowop[player][idx-2] += 1
        elif tmp[j+1] > tmp[j+4]:
            idx0, idx1 = idx - 1, idx + 1
            self.chowop[player][idx-1] += 1
        else:
            idx0, idx1 = idx + 1, idx + 2
            self.chowop[player][idx] += 1
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
        flag = 0
        # 加杠或暗杠
        if player == self.playerthis:
            idx = np.argmax(decision * (self.pongop[player] + self.pongcls[player]))
            flag += self.pongop[player][idx]
            if self.pongop[player][idx]:
                self.pongop[player][idx] = 0
                self.kongop[player][idx] = 1
            else:
                self.pongcls[player][idx] = 0
                self.kongcls[player][idx] = 1
        # 明杠
        else:
            self.liuman[self.playerthis] = 0
            self.playerthis = player
            self.clear[player] = 0
            self.shown[player][idx] = 1
            self.hands[player][idx] = 1
            self.dora[player][idx] = idx in self.doraid
            self.dorain[player][idx] = idx in self.dorainid
            idx %= 34
            self.pongcls[player][idx] = 0
            self.kongop[player][idx] = 1
        self.shown[player][idx::34] = 1
        self.unfixed[player][idx::34] = 0
        return flag
    
    def pongclsChecker(self):
        """Check the number of definite pong close this player has
        """
        # 应当在立直时确定所有的暗刻以防可能的暗杠改变听牌型
        player = self.playerthis
        cnt = self.hands[player].reshape([4, 34]).sum(0)
        assert all(cnt[self.kongcls[player]] == 4)
        cnt[self.kongcls[player]] = 0
        meldsall = []
        for idx in self.listen[player]:
            if idx:
                cnttmp = np.zeros(34, dtype='int')
                cnttmp[idx] = 1
                cnttmp += cnt
                meldsall += cntMeldsAll(cnttmp)
        # 只有所有听牌型下和牌后均为暗刻才是真的暗刻
        pongclsmelds = []
        for meld in meldsall[0]:
            for melds in meldsall:
                if meld[0] == meld[1] and meld[1] == meld[2] and meld in melds:
                    pongclsmelds.append(meld)
        colors = ['z', 's', 'p', 'm']
        for meld in pongclsmelds:
            self.pongcls[player][int(meld[0])+26-colors.index(meld[-1])*9] = 1
    
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
        statesAll = np.zeros([64, 34])
        statesAll[0] += self.bet / 2
        statesAll[1] += self.repeat / 2
        statesAll[2] += self.direction
        statesAll[3, np.array(self.doraid)[3::4]] = 1
        mountainview = np.zeros([4, 34])
        for i in range(4):
            for j in self.mountain[self.tilethis+i:self.tilethis+i+self.leftnum]:
                mountainview[i, j%34] += 1
        for player in range(4):
            statesAll[4+player] += self.points[player] / 8000
            statesAll[8+player] += self.river[player][self.doraid].sum()
            statesAll[12+player] += self.shown[player][self.doraid].sum()
            statesAll[16+player] += self.clear[player]
            statesAll[20+player] += self.riichi[player]
            statesAll[24+player] += self.dealer == player
            statesAll[28+player] += self.river[player].reshape([4, 34]]).sum(0)
            statesAll[32+player] += self.shown[player].reshape([4, 34]]).sum(0)
            # partial observable
            statesAll[36+player] += self.hands[player][self.doraid].sum()
            statesAll[40+player] += self.hands[player].reshape([4, 34]]).sum(0)
            statesAll[44+player] += self.unfixed[player].reshape([4, 34]]).sum(0)
            statesAll[48+player] += mountainview[player]
            statesAll[52+player] += mountainview[player-1]
            statesAll[56+player] += mountainview[player-2]
            statesAll[60+player] += mountainview[player-3]
        # 四人分别记录状态
        states = np.zeros([4, 64, 34])
        for player in range(4):
            states[player] += statesAll
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
    for i, color in enumerate(['z', 's', 'p', 'm']):
        melds3[i], melds2[i], melds, isomers[i] = cntMelds(cnt[27-i*9:36-i*9])
        if np.isnan(melds3[i]):
            return []
        meldsi.append(melds)
    assert melds3.sum() == np.sum(cnt)//3 and melds2.sum() == 1
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
                melds.append(str(tile+1) * num)
            if not (cntcnt[1] or cntcnt[4] or cntcnt[2] > 1):
                return cntcnt[3], cntcnt[2], [melds], 1
        elif len(cnt) == 9:
            childl = np.zeros(9)
            childr = np.zeros(9)
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
                        assert l3 == r3 + 2 and l2 = r2
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
        pt = np.ceil(int(np.ceil(fu / 10)) * pt / 10 * (2 ** (fan + 2))) * 100
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
