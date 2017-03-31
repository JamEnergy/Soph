from collections import OrderedDict
import os

def ensureDirs(path):
    components = os.path.normpath(path).split(os.sep)
    currentPath = os.getcwd()
    for comp in components:
        currentPath = os.path.join(currentPath, comp)
        ensureDir(currentPath)

def ensureDir(path):
    try:
        os.mkdir(path)
        return True
    except:
        if os.path.exists(path):
            return False
        raise

class SophDefaultDict(dict):
    def __init__(self, cb):
        super(SophDefaultDict, self).__init__()
        self.cb = cb

    def __missing__(self, key):
        new = self.cb(key)
        self[key] = new
        return new

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