import time
from collections import OrderedDict
class NoTimer:
    def __init__(self, key = "Unnamed", parent=None, duration = 0, printer=print):
        self.duration = 0
        pass
    def __enter__(self):
        return NoTimer()
        
    def output(self):
        pass
    def __exit__(self, a, b, c):
        pass
    def sub_timer(self, key):
        return NoTimer()

    def disable(self):
        pass

class Timer:
    def __init__(self, key = "Unnamed", parent=None, duration = 0, printer=print):
        self.parent = parent
        self.key = key
        self.sub_timers = OrderedDict()
        self.duration = duration
        self.printer = printer
        self.disabled = False

    def disable(self):
        self.disabled=True
    def __enter__(self):
        self.start = time.clock()
        return self

    def output(self):
        if self.disabled:
            return
        i = 0
        p = self
        while p:
            p = p.parent
            i += 1
        self.printer("{2}{0}: {1:.2f}s".format(self.key, self.duration, "  "*i))
        for k,v in self.sub_timers.items():
                v.output()

    def __exit__(self, a, b, c):
        self.end = time.clock()
        self.duration += (self.end-self.start)
        if self.parent:
            pass
        else:
            self.output()

    def sub_timer(self, key):
        if key in self.sub_timers:
            return self.sub_timers[key]
        else:
            sub = Timer(key=key, parent=self)
            self.sub_timers[key] = sub
            return sub



if __name__ == "__main__":
    with Timer("a") as t:
        with t.sub_timer("b") as s:
            for i in range(0,100):
                with s.sub_timer("c") as r:
                    pass