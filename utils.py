from functools import lru_cache
from os import listdir

import numpy as np

MAX_ROUNDS = 50
MAX_ACTIONS = 5000
COLORS = {'m':0, 'p':9, 's':18, 'z':27}
TILESTR = [str(i)+'m' for i in range(1, 10)] + \
    [str(i)+'p' for i in range(1, 10)] + \
    [str(i)+'s' for i in range(1, 10)] + \
    [str(i)+'z' for i in range(1, 8)]
IDX_TILER = dict([(i, TILESTR[i % 34]) for i in range(136)])
for c in sorted(COLORS)[:3]:
    IDX_TILER[106+COLORS[c]] = '0'+c
NOTAMELD = -100
N = len(listdir('./data/paipus/'))

def finder(uuids, uuid, shortest=10):
    n = len(uuids)
    if n < shortest:
        return uuid in uuids
    uuids = uuids[:n//2] if uuid < uuids[n//2] else uuids[n//2:]
    return finder(uuids, uuid)

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

@lru_cache()
def tileParser(tile):
    n = int(tile[0])
    c = COLORS[tile[1]]
    return n + c - 1 if n else 4 + c

def cntMeldsAll(cnt):
    melds3 = [0] * 4
    melds2 = [0] * 4
    meldsi = []
    isomers = [0] * 4
    for i in range(4):
        melds3[i], melds2[i], melds, isomers[i] = cntMelds(cnt[27-i*9:36-i*9])
        if melds3[i] < 0:
            return []
        meldsi.append(melds)
    if not (sum(melds3) == sum(cnt) // 3 and sum(melds2) == 1):
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
    if not (cntsum%3 == 1 or max(cnt) > 4): # 某种牌只可能有0~4张
        # 字牌
        if len(cnt) == 7:
            melds = []
            cntcnt = [0] * 5
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

@lru_cache()
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
        pt = [pti * 8000 * (fan // 13) for pti in pt]
    return pt

def argmax(x):
    m = max(x)
    return [i for i, j in enumerate(x) if m == j][0]
