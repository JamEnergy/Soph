import whoosh
from whoosh.fields import Schema, TEXT, ID ,KEYWORD
import os.path
from whoosh.index import create_in
import json
import re
import whoosh.scoring

class Index:
    schema = Schema(content=TEXT(stored=True), 
                user=ID(stored=True),
                mentionsUsers=KEYWORD(stored=True),
                mentionsRoles=KEYWORD(stored=True))

    def __init__(self, dir, authorIds = {}):
        self.ix = whoosh.index.open_dir(dir)
        
        self.authorIds = None
        self.authors = None
        self.setUsers(authorIds)

    def setUsers(self, authorIds):
        self.authorIds = authorIds
        self.authors = {k:v for v, k in authorIds.items()}

    def queryStats(self, text):
        """
            Returns a sorted tuple of (count, userName)
        """
        with self.ix.searcher() as searcher:
            from whoosh.qparser import QueryParser
            qp = QueryParser("content", schema=self.ix.schema)
            q = qp.parse(text)

            results = searcher.search(q, limit=100000)

            counts = {}

            for r in results:
                u = r["user"]
                if not u in counts:
                    counts[u] = 0
                counts[u] += 1
            
            counts = [(count, id) for id,count in counts.items() if count > 0]
            sc = reversed(sorted(counts))
            return [v for v in sc]

    def query(self, text, user = None):
        with self.ix.searcher(weighting = whoosh.scoring.TF_IDF) as searcher:
            from whoosh.qparser import QueryParser
            qp = QueryParser("content", schema=self.ix.schema)
            if user:
                textNode = qp.parse(text)
                textNode.fieldname = "content"

                userNode = whoosh.query.Term("user", user)

                q = whoosh.query.And([textNode, userNode]) 
            else:
                q = qp.parse(text)
            

            for i in range(0,3):
                results = searcher.search(q, limit=8 * (i+1))
                ret = [(r["user"], r["content"]) for r in results]

                exists = set()

                i = len(ret) - 1
                while i >= 0:
                    r = ret[i]
                    if not r[1] in exists:
                        exists.add(r[1])
                    else:
                        del ret[i]
                    i = i - 1

                #def cmp(x):
                #    return len(x[1])

                if len(ret) >= 3:
                    ret = ret[:3]
                    break

            return ret