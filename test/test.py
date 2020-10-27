import time

class A(object):
    def __init__(self, bfun):
        super().__init__()
        self.bfun = bfun
        self.data = [0, 1]
        
    def fun(self):
        print(self.bfun(self))
        raise NotImplementedError
        
class B(object):
    def __init__(self):
        super().__init__()
        self.data = [2, 3]
        
    def fun(self, aobj):
        data = self.data
        data[-1] = -1
        aobj.data[-1] = -2
        return aobj.data

class Ason(A):
    def __init__(self, bfun):
        super().__init__(bfun)
        # self.data = [1, 0]
    
    def fun(self):
        try:
            super().fun()
        except NotImplementedError:
            print('implemented now')
        finally:
            return self.data

def foo0():
    a = 0
    b = 1
    t0 = time.time()
    for _ in range(100000):
        _ = a or b
    t1 = time.time()
    for _ in range(100000):
        _ = a + b
    t2 = time.time()
    print('or: ', t1-t0, '+: ', t2-t1)

def foo1():
    a = 0
    b = 1
    t0 = time.time()
    for _ in range(100000):
        _ = a and b
    t1 = time.time()
    for _ in range(100000):
        _ = a * b
    t2 = time.time()
    print('and: ', t1-t0, '*: ', t2-t1)

def foo2():
    a = 2
    b = 2
    t0 = time.time()
    for _ in range(100000):
        _ = a is b
    t1 = time.time()
    for _ in range(100000):
        _ = a == b
    t2 = time.time()
    print('is: ', t1-t0, '==: ', t2-t1)

def foo3():
    a = []
    b = [1, 2]
    t0 = time.time()
    for _ in range(100000):
        b += a
    t1 = time.time()
    for _ in range(100000):
        b.extend(a)
    t2 = time.time()
    print('+=: ', t1-t0, 'extend: ', t2-t1)

if __name__ == "__main__":
    foo0()
    # b = B()
    # a = A(b.fun)
    # print(b.data, a.data)
    # ason = Ason(b.fun)
    # # print(ason.fun())
    # processnum = 30
    # subnum = 456195 // processnum
    # for i in range(processnum):
    #     print(f'python formatter.py {i*subnum+i//2:d} {(i+1)*subnum+(i+1)//2:d}')
