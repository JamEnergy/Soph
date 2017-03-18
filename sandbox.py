from collections import OrderedDict

class MRU:
    def __init__(self, size):
        self.map = OrderedDict()
        self.size = size

    def insert(self, k,v):
        if len(self.map) > self.size:
            self.map.popitem()
        self.map[k] = v

    def get(self, k):
        if k in self.map:
            self.map.move_to_end(k)
            return self.map[k]
        return None

m = Mru(1)

m.get(1)