import whoosh
from whoosh.fields import Schema, TEXT, ID ,KEYWORD
import os.path
from whoosh.index import create_in
import json
import re

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

            counts = {id:0 for id,name in self.authorIds.items()}

            for r in results:
                u = r["user"]
                counts[u] += 1
            
            counts = [(count, self.authorIds[id]) for id,count in counts.items() if count > 0]
            sc = reversed(sorted(counts))
            return [v for v in sc]