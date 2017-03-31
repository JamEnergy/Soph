import importlib
import os
import time

g_now = time.time()
g_modTimes = {}
def reload(module, filepath):
    """ reload module based on modified time of filepath"""
    global g_modTimes
    global g_now
    if not filepath in g_modTimes:
        g_modTimes[filepath] = g_now

    modTime = os.path.getmtime(filepath) 
    if modTime > g_modTimes[filepath]:
         g_modTimes[filepath] = modTime
         importlib.reload(module)
         return True

    return False