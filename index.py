import whoosh
from whoosh.fields import Schema, TEXT, ID ,KEYWORD
import os.path
from whoosh.index import create_in
import json
import re
import whoosh.scoring
from timer import Timer, NoTimer
from whoosh.qparser import QueryParser
from collections import defaultdict

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
        self.searchers = []

    class ScopedSearcher:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.handle = None
            self.args = kwargs

        def __enter__(self):
            try:
                self.handle = self.parent.searchers.pop()
                return self.handle
            except:
                self.handle = self.parent.ix.searcher(**self.args)
                return self.handle
        
        def __exit__(self,a,b,c):
            self.parent.searchers.append(self.handle)
            self.handle = None

    def getSearcher(self, **kwargs):
        return Index.ScopedSearcher(self, **kwargs)

    def setUsers(self, authorIds):
        self.authorIds = authorIds
        self.authors = {k:v for v, k in authorIds.items()}

    def queryStats(self, text, expand=False, timer=NoTimer()):
        """
            Returns a sorted tuple of (count, userName)
        """
        with timer.sub_timer("query-stats") as t:
            with self.getSearcher() as searcher:
                from whoosh.qparser import QueryParser
                if expand:
                    qp = QueryParser("content", schema=self.ix.schema, termclass=whoosh.query.Variations)
                else:
                    qp = QueryParser("content", schema=self.ix.schema)
                q = qp.parse(text)

                with t.sub_timer("searcher.search") as s:
                    results = searcher.search(q, limit=100000)

                with t.sub_timer("results") as s:
                    #counts = {}
                    counts = defaultdict( lambda: 0)
                    
                    with s.sub_timer("counts") as r:
                        for r in results:
                            u = r["user"]
                            counts[u] += 1
                    
                    with s.sub_timer("reverse") as r:
                        counts = [(count, id) for id,count in counts.items() if count > 0]
                        sc = reversed(sorted(counts))
                        return [v for v in sc]

    def deDupeResults(self, text, ret):
        exists = set([text.lower()])
        i = len(ret) - 1
        while i >= 0:
            r = ret[i]
            if not r[1].lower() in exists:
                exists.add(r[1].lower())
            else:
                del ret[i]
            i = i - 1
        return ret

    def queryLong(self, text, max = 3, user = None, expand=False, timer=NoTimer()):
        with timer.sub_timer("query-long") as t:
            for attempt in range(0,3):
                with t.sub_timer(attempt) as s:
                    results = self.query(text, max*(2+attempt), user, expand=(expand or (attempt > 0)), timer=timer)
                    ret = list(results)

                    if len(ret) >= max:
                        ret = ret[:max]
                        break
            return ret

    def queryUserOrI(self, text, max = 3, userId = None, userName = None, expand=False, dedupe=False):
        with self.getSearcher(weighting = whoosh.scoring.TF_IDF) as searcher:
            from whoosh.qparser import QueryParser
            qp = QueryParser("content", schema=self.ix.schema)
            i_node = qp.parse("I")
            i_node.fieldname = "content" # "I" in content

            userNode = whoosh.query.Term("user", userId) # userId in the user field

            user_i_node = whoosh.query.And([userNode])#, i_node])

            userTextNode = qp.parse(userName)
            userTextNode.fieldname = "content"

            subjectNode = whoosh.query.Or([userTextNode, user_i_node])

            qp2 = QueryParser("content", schema=self.ix.schema, termclass=whoosh.query.Variations)
            textNode = qp2.parse(text)
            textNode.fieldname = "content"

            q = whoosh.query.And([textNode, subjectNode])

            results = searcher.search(q, limit=max)

            results = [(r["user"], r["content"]) for r in results]

            results = self.deDupeResults(text, results)

            return results

    def query(self, text, max = 3, user = None, expand=False, nonExpandText=None, dedupe=False, timer=Timer("index.query")):
        with timer.sub_timer("query") as ot:
            with self.getSearcher(weighting = whoosh.scoring.TF_IDF) as searcher:
                with ot.sub_timer("inner-q") as t:
                    with t.sub_timer("query-parse") as s:
                        if expand:
                            qp = QueryParser("content", schema=self.ix.schema, termclass=whoosh.query.Variations)
                        else:
                            qp = QueryParser("content", schema=self.ix.schema)
                        nonExpandQP = QueryParser("content", schema=self.ix.schema)

                        if user:
                            textNode = qp.parse(text)
                            textNode.fieldname = "content"
                            userNode = whoosh.query.Term("user", user)
                            q = whoosh.query.And([textNode, userNode]) 
                        else:
                            q = qp.parse(text)
                            if nonExpandText:
                                q2 = nonExpandQP.parse(nonExpandText)
                                q = whoosh.query.And([q, q2])
                    
                    with t.sub_timer("searcher.search") as s:
                        results = searcher.search(q, limit=max)

                    with t.sub_timer("results") as s:
                        results = [(r["user"], r["content"]) for r in results]

                    if dedupe:
                        with t.sub_timer("dedupe") as s:
                            return self.deDupeResults(text, results)
                    else:
                        return results