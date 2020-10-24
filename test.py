class A(object):
    def __init__(self, bfun):
        super(A, self).__init__()
        self.bfun = bfun
        self.data = [0, 1, 2, 3]
        
    def fun(self):
        return self.bfun(self)
        
class B(object):
    def __init__(self):
        super(B, self).__init__()
        self.data = [0, 1, 2, 3]
        
    def fun(self, aobj):
        data = self.data
        data[-1] = 1
        return aobj.data[-1]
    
b = B()
a = A(b.fun)
print(a.fun(), b.data[-1])
