from random import shuffle

COLORS = {'m':0, 'p':9, 's':18, 'z':27}
TILESTR = [str(i)+'m' for i in range(1, 10)] + \
    [str(i)+'p' for i in range(1, 10)] + \
    [str(i)+'s' for i in range(1, 10)] + \
    [str(i)+'z' for i in range(1, 8)]
TILE_IDXMOD = dict([(t, i) for i, t in enumerate(TILESTR)])
IDX_TILE = dict([(i, TILESTR[i % 34]) for i in range(136)])
NOTAMELD = -100

class Game(object):
    def __init__(self, agents=None):
        super(Game, self).__init__()
        self.mountain = list(range(136)) # 牌山
        self.nonmiddle = [0, 8, 9, 17, 18, 26] + list(range(27, 34))
        self.nonmiddlechow = [0, 6, 9, 15, 18, 24]
        self.doramap = lambda i: (i + 1) % 9 + i // 9 * 9 if i < 27 \
            else (i - 6) % (3 + (i < 31)) + 31 - (i < 31) * 4 # 宝牌指示
        self.bet = 0        # 立直棒
        self.repeat = 0     # 本场棒
        self.direction = 0  # 场风
        self.dealer = 0     # 亲家
        self.roundid = -1     # 局数
        self.points = [25000] * 4 # 点数
        self.agents = agents
    
    def newRound(self):
        self.roundid += 1
        dealer = self.dealer
        mountain = self.mountain
        hands = [[0]*136, [0]*136, [0]*136, [0]*136]   # 手牌
        handscnt = [[0]*34, [0]*34, [0]*34, [0]*34]    # 手牌计数
        unfixed = [[0]*136, [0]*136, [0]*136, [0]*136] # 可以打出
        unfixedcnt = [[0]*34, [0]*34, [0]*34, [0]*34]  # 可以打出计数
        dora = [0]*4            # 宝牌
        dorain = [0]*4          # 里宝牌
        doraid = [self.doramap(mountain[-5] % 34)]   # 宝牌索引
        dorainid = [self.doramap(mountain[-6] % 34)] # 里宝牌索引
        # 发牌，标记宝牌
        for i in range(4):
            start = i * 13
            player = i + dealer - 4
            for j in mountain[start:start+13]:
                hands[player][j] = 1
                unfixed[player][j] = 1
                jmod = j % 34
                dora[player] += jmod in doraid
                dorain[player] += jmod in dorainid
                handscnt[player][jmod] += 1
                unfixedcnt[player][jmod] += 1
        
        self.hands = hands
        self.handscnt = handscnt
        self.unfixed = unfixed
        self.unfixedcnt = unfixedcnt
        self.dora = dora
        self.dorain = dorain
        self.doraid = doraid
        self.dorainid = dorainid

        self.shown = [[0]*136, [0]*136, [0]*136, [0]*136] # 可见（副露或暗杠）
        self.showncnt = [[0]*34, [0]*34, [0]*34, [0]*34]  # 可见（副露或暗杠）计数
        self.river = [[0]*136, [0]*136, [0]*136, [0]*136] # 牌河
        self.rivercnt = [[0]*34, [0]*34, [0]*34, [0]*34]  # 牌河计数
        
        self.playerthis = dealer  # 当前玩家
        self.tilethis = 52        # 当前摸牌
        self.doranum = 1          # 宝牌数
        self.leftnum = 70         # 余牌数

        self.grabkong = 0         # 抢杠
        self.ridgeview = 0        # 岭上开花
        self.liuju = 0            # 中途流局
        self.huangpai = 0         # 荒牌流局
        self.first = 1            # 第一巡
        self.riichi = [0]*4       # 立直
        self.abrupt = [0]*4       # 一发
        self.wriichi = [0]*4      # 两立直
        self.fritent = [0]*4      # 同巡振听
        self.fritens = [0]*4      # 舍张振听
        self.fritenl = [0]*4      # 立直振听
        self.roned = [0]*4        # 和了点数
        
        self.clear = [1]*4        # 门前清
        self.liuman = [1]*4       # 流局满贯
        
        self.listen = [[0]*34, [0]*34, [0]*34, [0]*34]  # 听牌
        self.chowop = [[0]*34, [0]*34, [0]*34, [0]*34]  # 明顺
        self.pongop = [[0]*34, [0]*34, [0]*34, [0]*34]  # 明刻
        self.pongcls = [[0]*34, [0]*34, [0]*34, [0]*34] # 暗刻
        self.kongop = [[0]*34, [0]*34, [0]*34, [0]*34]  # 明杠
        self.kongcls = [[0]*34, [0]*34, [0]*34, [0]*34] # 暗杠
        
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
        player = self.playerthis
        dealer = self.dealer
        handscnt = self.handscnt
        roned = self.roned
        bet = self.bet
        repeat = self.repeat
        ronAva = self.ronAva
        friten = [l+s+t for l, s, t in zip(self.fritenl, self.fritens, self.fritent)]
        if self.first and self.leftnum < 66:
            self.first = 0
        # 九种九牌
        if self.first and liujuDos[player] and sum([handscnt[player][i] > 0 for i in self.nonmiddle]) > 8:
            self.liuju = 1
            return False
        # 自摸
        fanBase, fan, fu = ronAva(idx, player, False)
        if fanBase > 0 and ronDos[player]:
            pt1, pt2, _, _ = cntPts(fan, fu)
            if dealer == player:
                for playeri in range(4):
                    if playeri == player:
                        roned[playeri] += pt2 * 3 + bet * 1000 + repeat * 300
                    else:
                        roned[playeri] -= pt2 + repeat * 100
            else:
                for playeri in range(4):
                    if playeri == player:
                        roned[playeri] += pt2 + pt1 * 2 + bet * 1000 + repeat * 300
                    elif playeri == dealer:
                        roned[playeri] -= pt2 + repeat * 100
                    else:
                        roned[playeri] -= pt1 + repeat * 100
            self.bet = 0
            return False
        # 杠
        if self.kongAva(idx, player) and kongDos[player]:
            # 若是加杠，需检查是否被抢杠，此处不考虑国士无双抢暗杠
            if self.kong(None, player, kongDecisions[player], None):
                self.grabkong = 1
                for position in range(3):
                    playeri = (player + position + 1) % 4
                    fanBase, fan, fu = ronAva(idx, playeri, False)
                    if fanBase > 0 and ronDos[playeri] and not friten[playeri]:
                        _, _, pt4, pt6 = cntPts(fan, fu)
                        pt = pt6 if dealer == playeri else pt4
                        roned[playeri] += pt + self.bet * 1000 + repeat * 300
                        roned[player] -= pt + repeat * 300
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
        player = self.playerthis
        dealer = self.dealer
        leftnum = self.leftnum
        rivercnt = self.rivercnt
        roned = self.roned
        repeat = self.repeat
        ronAva = self.ronAva
        kongAva = self.kongAva
        pongAva = self.pongAva
        friten = [l+s+t for l, s, t in zip(self.fritenl, self.fritens, self.fritent)]
        # 检查是否放铳，由于立直棒头跳，需要按顺序检查
        for position in range(3):
            playeri = (player + position + 1) % 4
            fanBase, fan, fu = ronAva(idx, playeri, False)
            if fanBase > 0 and ronDos[playeri] and not friten[playeri]:
                _, _, pt4, pt6 = cntPts(fan, fu)
                pt = pt6 if dealer == playeri else pt4
                roned[playeri] += pt + self.bet * 1000 + repeat * 300
                roned[player] -= pt + repeat * 300
                self.bet = 0
            # 不和则同巡振听
            if fanBase and not ronDos[playeri]:
                self.fritent[playeri] = 1
        if any(roned):
            return True
        # 未放铳进入一发巡，则立直成立
        elif self.abrupt[player]:
            self.bet += 1
            self.points[player] -= 1000
        # 明杠
        for playeri in range(4):
            if (not (playeri == player)) and kongAva(idx, playeri) and kongDos[playeri]:
                self.kong(idx, playeri, None, None)
                return True
        # 碰
        for playeri in range(4):
            if (not (playeri == player)) and pongAva(idx, playeri) and pongDos[playeri]:
                self.pong(idx, playeri, None, redfives[playeri])
                return False
        # 吃
        self.playerthis = (player + 1) % 4
        player = self.playerthis
        if self.chowAva(idx, None) and chowDos[player]:
            self.chow(idx, player, chowDecisions[player], redfives[player])
            return False
        # 四风连打，四杠散了
        if (leftnum == 66 and any([all([rivercnti[i] for rivercnti in rivercnt]) for i in range(27, 31)])) or \
            (self.doranum == 5 and max([sum(handscnti) for handscnti in self.handscnt]) < 17):
            self.liuju = 1
        # 荒牌流局
        if not leftnum:
            self.huangpai = 1
        return True
        
    def runRound(self, mountain=None):
        """Run a round

        Args:
            mountain (list, optional): mountain. Defaults to None.

        Returns:
            boolean: end of the game
        """
        if mountain is None:
            shuffle(self.mountain)
        else:
            self.mountain = mountain
        self.newRound()

        roned = self.roned
        draw = self.draw
        drawStep = self.drawStep
        discard = self.discard
        discardStep = self.discardStep
        agents = self.agents
        
        nextStep = True
        for _ in range(200):
            if self.liuju or self.huangpai or any(roned):
                break
            if nextStep:
                idx = draw()
                discardDecisions, _, kongDecisions, _, _, \
                    kongDos, ronDos, riichiDos, liujuDos, redfives = agents()
                nextStep = drawStep(
                    idx, kongDecisions, kongDos, ronDos, liujuDos
                )
                if nextStep: # 若仍是摸牌，需要重新决策
                    discardDecisions, _, kongDecisions, _, _, \
                        kongDos, ronDos, riichiDos, liujuDos, redfives = agents()
            else:
                player = self.playerthis
                idx = discard(
                    discardDecisions[player], riichiDos[player], redfives[player]
                )
                discardDecisions, chowDecisions, _, chowDos, pongDos, \
                    kongDos, ronDos, riichiDos, _, redfives = agents()
                nextStep = discardStep(
                    idx, chowDecisions, chowDos, pongDos, kongDos, ronDos, redfives
                )
                if not nextStep: # 若仍是切牌，需要重新决策
                    discardDecisions, chowDecisions, _, chowDos, pongDos, \
                        kongDos, ronDos, riichiDos, _, redfives = agents()
        
        lastdealer = self.dealer
        lastdirection = self.direction
        huangpai = self.huangpai
        points = self.points
        liuman = self.liuman
        if any(roned):
            self.bet = 0
            for playeri in range(4):
                points[playeri] += roned[playeri]
            # 亲家和则连庄，否则过庄
            if roned[lastdealer] > 0:
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
            listened = [sum(listeni) > 0 for listeni in self.listen]
            if any(listened) and not all(listened) and huangpai: # 或not self.leftnum
                for player in range(4):
                    if listened[player]:
                        points[player] += int(3000 / sum(listened))
                    else:
                        points[player] -= int(3000 / (4 - sum(listened)))
            # 流局满贯
            for playeri in range(4):
                if liuman[playeri]:
                    if playeri == lastdealer:
                        for i in range(4):
                            if i == playeri:
                                points[i] += 12000
                            else:
                                points[i] -= 4000
                    else:
                        for i in range(4):
                            if i == playeri:
                                points[i] += 8000
                            elif i == lastdealer:
                                points[i] -= 4000
                            else:
                                points[i] -= 2000
            # 荒牌流局且亲家未听则过庄
            if not listened[lastdealer] and huangpai: # 或not self.leftnum
                self.dealer += 1
                if self.dealer == 4:
                    self.dealer = 0
                    self.direction += 1
        direction = self.direction
        ko = min(points) < 0 # 击飞
        lastround = direction == 2 and max(points) > 30000 # 南四或西入
        northwin = argmax(points) == 3 and lastdirection == 1 and lastdealer == 3 # 南四亲一位
        finalround = direction == 3 # 无北入
        gameEnd = ko or lastround or northwin or finalround
        if gameEnd:
            points[argmax(points)] += self.bet * 1000
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
        
        isthis = self.playerthis == player
        kongclsi = self.kongcls[player]
        kongclsisum = sum(kongclsi)
        riichii = self.riichi[player]
        cleari = self.clear[player]
        nonmiddle = self.nonmiddle
        nonmiddlechow = self.nonmiddlechow
        # deep copy
        cntall = [i for i in self.handscnt[player]]
        
        idxmod = idx % 34
        if fast or not isthis:
            cntall[idxmod] += 1
        tiles = [i for i, cnti in enumerate(cntall) if cnti]
        kongeds = [i for i, konged in enumerate(kongclsi) if konged]
        for i in kongeds:
            assert cntall[i] > 3
            cntall[i] -= 4
        if riichii:
            cnt = cntall
        else:
            # deep copy
            cnt = [i for i in self.unfixedcnt[player]]
            if fast or not isthis:
                cnt[idxmod] += 1
        assert sum(cnt) % 3 == 2 # 若干面子加一将
        # 国士无双/国士无双十三面
        orphanscheck = [tile in nonmiddle for tile in tiles]
        thirteenorphans = len(tiles) == 13 and all(orphanscheck)
        # 七对子（也可能是两杯口，后续区分）
        sevenpairs = len(tiles) == 7 and all([cnt[tile] == 2 for tile in tiles]) and cleari
        # 面子手
        meldsall = cntMeldsAll(cnt)
        ronmelds = len(meldsall)
        listenedi = ronmelds or thirteenorphans or sevenpairs
        if fast: # 只是用来判断是否听牌
            return listenedi
        # 未听
        if not listenedi:
            return 0, 0, 0
        
        kongopi = self.kongop[player]
        pongopi = self.pongop[player]
        chowopi = self.chowop[player]
        kongopisum = sum(kongopi)
        pongopisum = sum(pongopi)
        chowopisum = sum(chowopi)
        
        green = [19, 20, 21, 23, 25, 32]
        red = [106, 115, 124]
        beikou = [0, 1, 2]
        pongopall = [i+j+k for i, j, k in zip(pongopi, kongclsi, kongopi)]
        pongopallsum = sum(pongopall)
        nonmiddleall = sum([pongopall[i] for i in nonmiddle]) == pongopallsum and \
            sum([chowopi[i] for i in nonmiddlechow]) == chowopisum

        yiman = 0
        mian = sum(self.listen[player])
        # 天和/地和
        tiandi = self.first and isthis
        if sevenpairs and tiandi:
            return 13, 13, 25
        # 立直，两立直，一发，抢杠，岭上开花，门清自摸，海底摸月/河底捞鱼，断幺九，混老头
        fan = riichii + self.wriichi[player] + self.abrupt[player] + \
            self.grabkong + self.ridgeview + (cleari and isthis) + (not self.leftnum) + \
            (not any(orphanscheck)) + all(orphanscheck) * 2
        # 染手
        singlecolor = list(set([tile // 9 for tile in tiles]))
        numcolor = len(singlecolor)
        zincolor = 3 in singlecolor # 判断有没有字牌
        if numcolor == 1:
            if zincolor:
                # 字一色
                yiman += 1
            else:
                # 清一色
                fan += 5 + cleari
                # 九莲宝灯/纯正九莲宝灯
                tmp = tiles[0] // 9 * 9
                # 纯正九莲宝灯听牌时为311111113，9面听
                yiman += (cleari and not any(kongclsi)) * ((mian == 9) + \
                    (all([i - ((i - 1) % 2) == 1 for i in cnt[tmp+1:tmp+8]]) and \
                    all([i - ((i - 1) % 2) == 3 for i in [cnt[tmp], cnt[tmp+8]]])))
        # 混一色
        if numcolor == 2 and zincolor:
            fan += 2 + cleari
        # 宝牌/红宝牌，里宝牌
        fandora = self.dora[player] + sum(self.hands[player][106:133:9]) + \
            self.dorain[player] * riichii
        if not isthis:
            fandora += (idxmod in self.doraid) + (idx in red) + \
                (idxmod in self.dorainid) * riichii
        # 七对子固定25符
        if sevenpairs and not ronmelds:
            return fan + 2, fan + 2 + fandora, 25
        melds0 = meldsall[0]
        # 绿一色，清老头，四杠子，大三元，大四喜，小四喜，国士无双，国士无双十三面
        yiman += tiandi + \
            all([tile in green for tile in tiles]) + \
            all([tile in nonmiddle[:6] for tile in tiles]) + \
            (kongclsisum + kongopisum == 4) + \
            all([pongopall[i] or any([meld[2:] == IDX_TILE[i] for meld in melds0]) for i in range(31, 34)]) + \
            all([pongopall[i] or any([meld[2:] == IDX_TILE[i] for meld in melds0]) for i in range(27, 31)]) + \
            all([pongopall[i] or any([meld[-2:] == IDX_TILE[i] for meld in melds0]) for i in range(27, 31)]) + \
            thirteenorphans + (mian == 13)
        # 小三元
        fan += all([pongopall[i] or any([meld[-2:] == IDX_TILE[i] for meld in melds0]) for i in range(31, 34)]) * 2      
        # 自风，场风，役牌
        yiall = [(player - self.dealer) % 4, self.direction, 4, 5, 6]
        fan += sum([any([meld[2:] == IDX_TILE[yi+27] for meld in melds0]) or pongopall[yi+27] for yi in yiall])
        fu = any([any([meld[1:] == IDX_TILE[yi+27] for meld in melds0]) for yi in yiall]) * 2 + \
            pongopisum * 2 + kongopisum * 8 + kongclsisum * 16 + \
            sum([pongopi[i]*2 + kongopi[i]*8 + kongclsi[i]*16 for i in nonmiddle])
        # 三杠子
        fan += (kongclsisum + kongopisum == 3) * 2
        # 高点原则
        fanmax = 0
        fumax = 0
        yimanmax = 0
        rontile = IDX_TILE[idx]
        for melds in meldsall:
            fantmp = 0
            futmp = fu
            yimantmp = 0
            nonmiddletmp = [meld[0] == '1' or meld[-2] == '9' or meld[-1] == 'z' for meld in melds]
            # 暗刻数
            pongclstmp = [meld[1] == meld[2] and (isthis or not rontile == meld[2:]) for meld in melds]
            npongcls = sum(pongclstmp)
            npongclsron = any([meld[1] == meld[2] and (isthis and rontile == meld[2:]) for meld in melds])
            npongclsnonmiddle = sum([i and j for i, j in zip(nonmiddletmp, pongclstmp)])
            # 四暗刻/四暗刻单骑（暗杠也是暗刻）
            yimantmp += (kongclsisum + npongcls == 4) * (2 - npongclsron)
            # 三暗刻（暗杠也是暗刻）
            fantmp += (kongclsisum + npongcls == 3) * 2
            # 三色同刻
            fantmp += any([
                sum(pongopall[i:27:9]) + sum([str(i+1) == meld[2] and meld[1] == meld[2] for meld in melds]) == 3 \
                for i in range(9)
            ]) * 2
            # 三色同顺
            fantmp += any([
                min([
                    k + j for k, j in zip(
                        chowopi[i:27:9], [str(111*i+123)+c in melds for c in sorted(COLORS)[:3]]
                        )
                ])
                for i in range(7)
            ]) * (1 + cleari)
            # 对对和
            fantmp += (pongopallsum + sum([meld[1] == meld[2] for meld in melds]) == 4) * 2
            # 一杯口/两杯口
            fantmp += sum(beikou[:1+[melds.count(meld) for meld in set(melds)].count(2)]) * cleari
            # 混全带幺九
            fantmp += (nonmiddleall and all(nonmiddletmp)) * (1 + cleari)
            # 纯全带幺九（多一番）
            fantmp += all([meld[0] == '1' or meld[-2] == '9' for meld in melds]) and \
                    sum(pongopall[i] for i in nonmiddle[:6]) == pongopallsum
            # 一气通贯
            isseq = [all(cntall[i*9:i*9+9]) for i in range(3)]
            if any(isseq):
                isseqc = isseq.index(1)
                fantmp += (len(cntMeldsAll([j - (i // 9 == isseqc) for i, j in enumerate(cntall)])) > 0) * (1 + cleari)
            # 算符
            futmp += npongcls * 4 + npongclsnonmiddle * 4
            # 平和
            ping = cleari and not futmp and any([
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
            if isthis:
                futmp += 2 * (not ping)
            elif cleari:
                futmp += 10
            # 一番20符作一番30符处理
            if fan + fantmp == 1 and not (futmp or fandora):
                futmp = 10
            futmp = (futmp // 10 + (futmp % 10 > 0)) * 10
            if fantmp > fanmax:
                fanmax = fantmp
                fumax = futmp
            elif fantmp == fanmax and futmp > fumax:
                fanmax = fantmp
                fumax = futmp   
        fan += fanmax
        # 无役听牌
        if ronmelds and not fan:
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
        return self.leftnum and self.unfixedcnt[player][idx%34] > 1  # 最后一张不能碰
    
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
        tmp = [0, 0] + self.unfixedcnt[self.playerthis][i:i+9] + [0, 0]
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
        unfixedcnti = self.unfixedcnt[player]
        if player == self.playerthis: # 加杠或暗杠
            if self.riichi[player]: # 立直后暗刻才能暗杠
                flag += self.pongcls[player][idxmod]
            else:
                pongopi = self.pongop[player]
                flag = max(unfixedcnti) == 4 or any([i and j for i, j in zip(pongopi, unfixedcnti)])
        else: # 明杠
            flag = unfixedcnti[idxmod] == 3
        return self.leftnum and flag  # 最后一张不能杠
    
    def draw(self):
        """Draw a tile

        Returns:
            int: index of the tile
        """
        ridgeview = self.ridgeview 
        tilethis = -self.doranum if ridgeview else self.tilethis
        mountain = self.mountain
        idx = mountain[tilethis]
        player = self.playerthis
        idxmod = idx % 34
        self.hands[player][idx] = 1
        self.handscnt[player][idxmod] += 1
        self.unfixed[player][idx] = 1
        self.unfixedcnt[player][idxmod] += 1
        self.dora[player] += idxmod in self.doraid
        self.dorain[player] += idxmod in self.dorainid
    
        if ridgeview:
            self.doranum += 1
            doranum = self.doranum
            assert doranum < 6
            doramap = self.doramap
            newdoraid = doramap(mountain[-3-doranum*2]%34)
            self.doraid.append(newdoraid)
            newdorainid = doramap(mountain[-4-doranum*2]%34)
            self.dorainid.append(newdorainid)
            handscnt = self.handscnt
            for i, handscnti in enumerate(handscnt):
                self.dora[i] += handscnti[newdoraid]
                self.dorain[i] += handscnti[newdorainid]
        else:
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
        player = self.playerthis
        unfixedi = self.unfixed[player]
        unfixedcnti = self.unfixedcnt[player]
        decisioni = [i * (j > 0) for i, j in zip(decision, unfixedcnti)]
        idxmod = argmax(decisioni)
        nonmiddle = self.nonmiddle
        if not (idxmod in nonmiddle):
            self.liuman[player] = 0
        rng = list(range(idxmod, 136, 34))
        if redfive:
            rng.reverse()
        flag = 0
        for idx in rng:
            if unfixedi[idx]:
                self.river[player][idx] = 1
                self.rivercnt[player][idxmod] += 1
                self.hands[player][idx] = 0
                self.handscnt[player][idxmod] -= 1
                self.dora[player] -= idxmod in self.doraid
                self.dorain[player] -= idxmod in self.dorainid
                unfixedi[idx] = 0
                unfixedcnti[idxmod] -= 1
                flag = 1
                break
        assert flag
        abrupt = self.abrupt
        riichi = self.riichi
        if abrupt[player]:
            abrupt[player] = 0
        ronAva = self.ronAva
        newlisten = [ronAva(i, player, True) for i in range(34)]
        listened = any(newlisten)
        self.listen[player] = newlisten
        rivercnti = self.rivercnt[player]
        if listened:
            self.fritens[player] = any([rivercnti[i] and newlisten[i] for i in range(34)])
            if riichiDo and self.points[player] > 1000 and self.clear[player] and not riichi[player]:
                riichi[player] = 1
                abrupt[player] = 1
                self.wriichi[player] = self.first
                unfixedi = [0] * 136
                unfixedcnti = [0] * 34
                self.pongclsChecker()
        if riichi[player] and self.fritens[player]:
            self.fritenl[player] = 1
        self.fritent[player] = 0
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
        self.abrupt = [0] * 4
        self.first = 0
        self.liuman[self.playerthis] = 0
        self.playerthis = player
        self.clear[player] = 0
        idxmod = idx % 34
        showni = self.shown[player]
        showncnti = self.showncnt[player]
        showni[idx] = 1
        showncnti[idxmod] += 1
        self.hands[player][idx] = 1
        self.handscnt[player][idxmod] += 1
        self.dora[player] += idxmod in self.doraid
        self.dorain[player] += idxmod in self.dorainid
        self.pongop[player][idxmod] = 1
        rng = list(range(idxmod, 136, 34))
        if redfive:
            rng.reverse()
        flag = 0
        unfixedi = self.unfixed[player]
        unfixedcnti = self.unfixedcnt[player]
        for i in rng:
            if unfixedi[i]:
                showni[i] = 1
                showncnti[idxmod] += 1
                unfixedi[i] = 0
                unfixedcnti[idxmod] -= 1
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
        self.abrupt = [0] * 4
        self.first = 0
        assert player == self.playerthis
        self.liuman[player-1] = 0
        self.clear[player] = 0
        idxmod = idx % 34
        showni = self.shown[player]
        showncnti = self.showncnt[player]
        showni[idx] = 1
        showncnti[idxmod] += 1
        self.hands[player][idx] = 1
        self.handscnt[player][idxmod] += 1
        self.dora[player] += idxmod in self.doraid
        self.dorain[player] += idxmod in self.dorainid
        i, j = idxmod // 9 * 9, idxmod % 9
        unfixedi = self.unfixed[player]
        unfixedcnti = self.unfixedcnt[player]
        decisioni = [i * (j > 0) for i, j in zip(decision, unfixedcnti)]
        tmp = [0, 0] + decisioni[i:i+9] + [0, 0]
        if tmp[j] > tmp[j+3] and tmp[j] + tmp[j+1] > tmp[j+3] + tmp[j+4]:
            idx0, idx1 = idxmod - 2, idxmod - 1
            self.chowop[player][idxmod-2] += 1
        elif tmp[j+1] > tmp[j+4]:
            idx0, idx1 = idxmod - 1, idxmod + 1
            self.chowop[player][idxmod-1] += 1
        else:
            idx0, idx1 = idxmod + 1, idxmod + 2
            self.chowop[player][idxmod] += 1
        rng0 = list(range(idx0, 136, 34))
        if redfive:
            rng0.reverse()
        flag0 = 0
        for i in rng0:
            if unfixedi[i]:
                showni[i] = 1
                showncnti[idx0] += 1
                unfixedi[i] = 0
                unfixedcnti[idx0] -= 1
                flag0 = 1
                break
        assert flag0
        rng1 = list(range(idx1, 136, 34))
        if redfive:
            rng1.reverse()
        flag1 = 0
        for i in rng1:
            if unfixedi[i]:
                showni[i] = 1
                showncnti[idx1] += 1
                unfixedi[i] = 0
                unfixedcnti[idx1] -= 1
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
        self.abrupt = [0] * 4
        self.first = 0
        self.ridgeview = 1 # 下一张从岭上摸牌
        showni = self.shown[player]
        showncnti = self.showncnt[player]
        unfixedi = self.unfixed[player]
        unfixedcnti = self.unfixedcnt[player]
        flag = 0
        # 加杠或暗杠
        if player == self.playerthis:
            pongclsi = self.pongcls[player]
            pongopi = self.pongop[player]
            pongclsmelds = pongclsi if self.riichi[player] else [i == 4 for i in unfixedcnti]
            decisioni = [i * (j + k > 0) for i, j, k in zip(decision, pongclsmelds, pongopi)]
            idxmod = argmax(decisioni)
            flag += pongopi[idxmod]
            if pongopi[idxmod]:
                pongopi[idxmod] = 0
                self.kongop[player][idxmod] = 1
            else:
                pongclsi[idxmod] = 0
                self.kongcls[player][idxmod] = 1
        # 明杠
        else:
            self.liuman[self.playerthis] = 0
            self.playerthis = player
            self.clear[player] = 0
            idxmod = idx % 34
            self.hands[player][idx] = 1
            self.handscnt[player][idxmod] += 1
            self.dora[player] += idxmod in self.doraid
            self.dorain[player] += idxmod in self.dorainid
            self.pongcls[player][idxmod] = 0
            self.kongop[player][idxmod] = 1
        unfixedi[idxmod] = 0
        unfixedi[idxmod+34] = 0
        unfixedi[idxmod+2*34] = 0
        unfixedi[idxmod+3*34] = 0
        unfixedcnti[idxmod] = 0
        showni[idxmod] = 1
        showni[idxmod+34] = 1
        showni[idxmod+2*34] = 1
        showni[idxmod+3*34] = 1
        showncnti[idxmod] = 4
        return flag
    
    def pongclsChecker(self):
        """Check the number of definite pong close this player has
        """
        # 应当在立直时确定所有的暗刻以防可能的暗杠改变听牌型
        player = self.playerthis
        handscnti = self.handscnt[player]
        kongclsi = self.kongcls[player]
        pongclsi = self.pongcls[player]
        # deep copy
        cnt = [i for i in handscnti]
        kongeds = [i for i, konged in enumerate(kongclsi) if konged]
        for i in kongeds:
            assert cnt[i] > 3
            cnt[i] -= 4
        listeni = self.listen[player]
        listening = [i for i, j in enumerate(listeni) if j]
        meldsall = []
        for i in listening:
            cnttmp = [k + (j == i) for j, k in enumerate(cnt)]
            meldsall += cntMeldsAll(cnttmp)
        if len(meldsall):
            # 只有所有听牌型下和牌后均为暗刻才是真的暗刻
            pongclstiles = [meld[-2:] for meld in meldsall[0] if \
                len(meld) == 4 and meld[1] == meld[2] and all([meld in melds for melds in meldsall])]
            for tile in pongclstiles:
                pongclsi[TILE_IDXMOD[tile]] = 1
        
def cntMeldsAll(cnt):
    melds3 = [0] * 4
    melds2 = [0] * 4
    meldsi = []
    isomers = [0] * 4
    for i, color in enumerate(reversed(sorted(COLORS))):
        melds3[i], melds2[i], melds, isomers[i] = cntMelds(cnt[27-i*9:36-i*9])
        if melds3[i] < 0:
            return []
        meldsi.append(melds)
    if not sum(melds3) == sum(cnt) // 3 and sum(melds2) == 1:
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
    cntsum = sum(cnt)
    if not (cntsum%3 == 1):
        # 字牌
        if len(cnt) == 7:
            melds = []
            cntcnt = [0] * 5 # 某种字牌可能有0~4张
            for tile, num in enumerate(cnt):
                cntcnt[num] += 1
                if num:
                    melds.append(str(tile+1) * num)
            if not (cntcnt[1] or cntcnt[4] or cntcnt[2] > 1):
                return cntcnt[3], cntcnt[2], [melds], 1
        elif len(cnt) == 9:
            childl = [0] * 9
            childr = [0] * 9
            l3 = NOTAMELD
            r3 = NOTAMELD
            # disconnect
            for i in range(1, 8):
                if cnt[i-1] and sum(cnt[i+1:]) and not cnt[i]:
                    childl = cnt[:i] + [0] * (9 - i)
                    childr = [0] * i + cnt[i:]
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
            cntmax = max(cnt)
            cntpos = argmax(cnt)
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
            # for i, j in enumerate(cnt):
            #     if j:
            #         break
            i = [j > 0 for j in cnt].index(True)
            if i > 6: # only 8 or 9, can not form meld
                melds = []
                cntcnt = [0] * 5
                for tile, num in enumerate(cnt):
                    cntcnt[num] += 1
                    if num:
                        melds.append(str(tile+1) * num)
                if not (cntcnt[1] or cntcnt[4] or cntcnt[2] > 1):
                    return cntcnt[3], cntcnt[2], [melds], 1
            elif cnt[i] == 1 or cnt[i] == 4: # 一定有至少一个顺子
                if cnt[i+1] and cnt[i+2]:
                    childl = [k-(i-1<j and j<i+3) for j, k in enumerate(cnt)]
                    l3, l2, lm, li = cntMelds(childl)
                    if l3 >= 0:
                        lm = [lmi + [str(i+1)+str(i+2)+str(i+3)] for lmi in lm]
                        return l3 + 1, l2, lm, li
            elif cnt[i] == 2:
                # 做将或有一杯口形状
                childl = [k-(i==j)*2 for j, k in enumerate(cnt)]
                l3, l2, lm, li = cntMelds(childl)
                if cnt[i+1] > 1 and cnt[i+2] > 1: 
                    childr = [k-(i-1<j and j<i+3)*2 for j, k in enumerate(cnt)]
                    r3, r2, rm, ri = cntMelds(childr)
                if l3 >= 0:
                    lm = [lmi + [str(i+1)*2] for lmi in lm]
                    l2 += 1
                    if r3 >= 0:
                        if l3 == r3 + 2 and l2 == r2:
                            rm = [rmi + [str(i+1)+str(i+2)+str(i+3)]*2 for rmi in rm]
                            lm += rm
                            li += ri
                    return l3, l2, lm, li
                elif r3 >= 0:
                    rm = [rmi + [str(i+1)+str(i+2)+str(i+3)]*2 for rmi in rm]
                    r3 += 2
                    return r3, r2, rm, ri
            else: # 做刻或做将或有三杯口形状
                # 虽然三杯口是三暗刻，但是在最本格的规则里需要区分，因为三暗刻未必是三杯口
                childl = [k-(i==j)*3 for j, k in enumerate(cnt)]
                l3, l2, lm, li = cntMelds(childl)
                if cnt[i+1] and cnt[i+2]: # 做将或三杯口形状一定有至少一个顺子
                    childr = [k-(i-1<j and j<i+3) for j, k in enumerate(cnt)]
                    r3, r2, rm, ri = cntMelds(childr)
                if l3 >= 0:
                    lm = [lmi + [str(i+1)*3] for lmi in lm]
                    l3 += 1
                    if r3 >= 0:
                        rm = [rmi + [str(i+1)+str(i+2)+str(i+3)] for rmi in rm]
                        lm += rm
                        li += ri
                    return l3, l2, lm, li
                elif r3 >= 0:
                    rm = [rmi + [str(i+1)+str(i+2)+str(i+3)] for rmi in rm]
                    r3 += 1
                    return r3, r2, rm, ri
    return NOTAMELD, NOTAMELD, [[]], 0

def cntPts(fan, fu):
    pt = [1, 2, 4, 6]
    if not ((fan == 4 and fu > 30) or (fan == 3 and fu > 60) or fan > 4):
        pt = [fu * pti * (2 ** (fan + 2)) for pti in pt]
        pt = [(pti // 100 + (pti % 100 > 0)) * 100 for pti in pt]
    elif fan < 6:
        pt = [pti * 2000 for pti in pt]
    elif fan < 8:
        pt = [pti * 3000 for pti in pt]
    elif fan < 11:
        pt = [pti * 4000 for pti in pt]
    elif fan < 13:
        pt = [pti * 6000 for pti in pt]
    else:
        pt = [pti * 8000 for pti in pt]
    return pt

def argmax(x):
    m = max(x)
    return [i for i, j in enumerate(x) if m == j][0]
