import spacy
from concurrent.futures import ThreadPoolExecutor

def load():
    nlp = spacy.load("en")
    return nlp

pool = ThreadPoolExecutor(1)
future = pool.submit(load) 

class get:
    def __call__(self, *pargs):
        global future
        nlp = future.result()
        return nlp(*pargs)
