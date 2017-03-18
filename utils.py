from collections import OrderedDict

class MRU:
    def __init__(self, size):
        self.map = OrderedDict()
        self.size = size

    def insert(self, k,v):
        if not k in self.map:
            if len(self.map) >= self.size:
                self.map.popitem(last=False)
        self.map[k] = v
        self.map.move_to_end(k)

    def get(self, k):
        if k in self.map:
            self.map.move_to_end(k)
            return self.map[k]
        return None