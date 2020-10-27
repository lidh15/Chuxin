import numpy as np


def hands_test(cnt):
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
        l3, l2, lm, li = hands_test(childl)
        r3, r2, rm, ri = hands_test(childr)
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
            l3, l2, lm, li = hands_test(childl)
            if not np.isnan(l3):
                lm = [lmi + [str(i+1)+str(i+2)+str(i+3)] for lmi in lm]
                return l3 + 1, l2, lm, li
    elif cnt[i] == 2:
        # 做将或有一杯口形状
        childl += cnt
        childl[i] -= 2
        l3, l2, lm, li = hands_test(childl)
        if cnt[i+1] > 1 and cnt[i+2] > 1: 
            childr += cnt
            childr[i:i+3] -= 2
            r3, r2, rm, ri = hands_test(childr)
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
        l3, l2, lm, li = hands_test(childl)
        if cnt[i+1] and cnt[i+2]: # 做将或三杯口形状一定有至少一个顺子
            childr += cnt
            childr[i:i+3] -= 1
            r3, r2, rm, ri = hands_test(childr)
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

# npless version
NOTAMELD = -100
argmax = np.argmax

def hands_test_(cnt):
    cntsum = sum(cnt)
    if not (cntsum % 3 == 1):
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
            l3, l2, lm, li = hands_test_(childl)
            r3, r2, rm, ri = hands_test_(childr)
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
                l3, l2, lm, li = hands_test_(childl)
                if l3 >= 0:
                    lm = [lmi + [str(i+1)+str(i+2)+str(i+3)] for lmi in lm]
                    return l3 + 1, l2, lm, li
        elif cnt[i] == 2:
            # 做将或有一杯口形状
            childl = [k-(i==j)*2 for j, k in enumerate(cnt)]
            l3, l2, lm, li = hands_test_(childl)
            if cnt[i+1] > 1 and cnt[i+2] > 1: 
                childr = [k-(i-1<j and j<i+3)*2 for j, k in enumerate(cnt)]
                r3, r2, rm, ri = hands_test_(childr)
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
            l3, l2, lm, li = hands_test_(childl)
            if cnt[i+1] and cnt[i+2]: # 做将或三杯口形状一定有至少一个顺子
                childr = [k-(i-1<j and j<i+3) for j, k in enumerate(cnt)]
                r3, r2, rm, ri = hands_test_(childr)
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

print(hands_test_(np.array([0, 3, 1, 2, 1, 1, 0, 0, 0], dtype='int')))
