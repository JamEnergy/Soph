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

    def queryStats(self, text, expand=False):
        """
            Returns a sorted tuple of (count, userName)
        """
        with self.ix.searcher() as searcher:
            from whoosh.qparser import QueryParser
            if expand:
                qp = QueryParser("content", schema=self.ix.schema, termclass=whoosh.query.Variations)
            else:
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

    def queryLong(self, text, max = 3, user = None, expand=False):
        for attempt in range(0,3):
            results = self.query(text, max*(1+attempt), user, expand=(expand or (attempt > 0)))
            ret = list(results)

            exists = self.deDupeResults(text, ret)

            if len(ret) >= max:
                ret = ret[:max]
                break

        return ret

    def queryUserOrI(self, text, max = 3, userId = None, userName = None, expand=False, dedupe=False):
        with self.ix.searcher(weighting = whoosh.scoring.TF_IDF) as searcher:
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

    def query(self, text, max = 3, user = None, expand=False, nonExpandText=None, dedupe=False):
        with self.ix.searcher(weighting = whoosh.scoring.TF_IDF) as searcher:
            from whoosh.qparser import QueryParser
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
            
            results = searcher.search(q, limit=max)

            results = [(r["user"], r["content"]) for r in results]

            if dedupe:
                return self.deDupeResults(text, results)
            else:
                return results