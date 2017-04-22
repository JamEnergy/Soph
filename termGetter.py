import index
import os
import asyncio
from concurrent.futures import ProcessPoolExecutor

def run(sid, names):
    ind = index.Index(os.path.join("data", str(sid), "index"), 
                      start = False)

    return ind.terms(names, 0, True, 0)

async def term_getter(loop, executor, sid, names):
    
    return await loop.run_in_executor(executor, run, (sid, names))
    