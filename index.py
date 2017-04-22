import whoosh
from whoosh.fields import Schema, TEXT, ID ,KEYWORD, DATETIME, NUMERIC
import shutil
import os.path
from whoosh.index import create_in
import json
import re
import whoosh.scoring
from timer import Timer, NoTimer
from whoosh.qparser import QueryParser
from collections import defaultdict
import threading
import datetime
import time
import utils
from whoosh.util.text import rcompile

class Results:
    def __init__(self, gen, dedupe=True):
        self.dedupe = dedupe
        self.gen = gen
        self.seen = set([])
        self.field = "content"

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            candidate = next(self.gen) # or throw stopiteration
            if self.dedupe and candidate[self.field] in self.seen:
                continue
            if self.dedupe:
                self.seen.add(candidate[self.field])
            return (candidate["user"], candidate[self.field])

def deduper(it, dedupe=True, field="content"):
    seen = set([])
    for item in it:
        if dedupe and item[field] in seen:
                continue
        if dedupe:
            seen.add(item[field])
        yield (item["user"], item[field])
    return None

tok_pat = rcompile(r"[+£€]?\w+(\.?\w+)*")
STOP_WORDS = frozenset(('a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'can',
                        'for', 'from', 'have', 'if', 'in', 'is', 'it', 'may',
                        'not', 'of', 'on', 'or', 'tbd', 'that', 'the', 'this',
                        'to', 'when', 'will', 'with', 'yet'))
def Analyzer(expression=tok_pat, stoplist=None, minsize=1, maxsize=None, gaps=False):
    if stoplist is None:
        stoplist = STOP_WORDS
    return whoosh.analysis.StandardAnalyzer(expression=expression, 
                                            stoplist=stoplist,
                                            minsize=minsize, 
                                            maxsize=maxsize, 
                                            gaps=gaps)
class Index:
    schema = Schema(content=TEXT(stored=True, analyzer=Analyzer()), 
                    user=ID(stored=True),
                    mentionsUsers=KEYWORD(stored=True),
                    mentionsRoles=KEYWORD(stored=True),
                    time=DATETIME)

    def __init__(self, dir, authorIds = {}, context = None, start=True, baseDir=None):
        if not os.path.isdir(dir):
            os.mkdir(dir)

        if not list(os.listdir(dir)):
            self.ix = create_in(dir, Index.schema)

        if not baseDir:
            baseDir = os.path.join(os.path.split(dir)[0])

        self.ix = whoosh.index.open_dir(dir)
        self.searchers = []
        self.failedDir = os.path.join(baseDir, "failed")
        utils.ensureDir(self.failedDir)
        self.incomingDir = os.path.join(baseDir, "incoming")
        utils.ensureDir(self.incomingDir)
        self.indexer = threading.Thread(target = Index.indexLoop, args=[self])
        self.logger = open(os.path.join(baseDir,"index.log"), "a")
        self.stopping = False
        if start:
            self.startIndexer()
        self.counts = {}

    def getCounts(self, uid):
        if uid in self.counts:
            return self.counts[uid]
        else:
            with self.getSearcher() as searcher:
                userNode = whoosh.query.Term("user", uid) # userId in the user field
                
                results = searcher.search(userNode)
                self.counts[uid] = len(results)
                return len(results)

    def getLast(self, uid, number):
        with self.getSearcher() as searcher:
            userNode = whoosh.query.Term("user", uid) # userId in the user field
                
            results = searcher.search(userNode, 
                                      #sortedby="time", 
                                      limit=number)
            return deduper(results, dedupe = True)

    def startIndexer(self):
        self.indexer.start()
        self.stopping = False
        
    def __del__(self):
        self.stopping = True
        if self.indexer.is_alive():
            self.indexer.join()

    def log(self, text):
        print (text)
        self.logger.write(text)
        self.logger.write("\n")
        self.logger.flush()

    def indexLoop(self):
        print ("Beginning index loop")
        writer = self.ix.writer()
        while not self.stopping:
            path = None
            try:
                for file in os.listdir(self.incomingDir):
                    self.log("indexing {0}\n".format(file))
                    path = os.path.join(self.incomingDir, file)
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            doc = json.loads(line)
                            ts = doc["timestamp"]
                            t = datetime.datetime.fromtimestamp(ts)
                            userid = "{0}".format(doc["user"])
                            writer.add_document(content=doc["content"].strip(), 
                                                user=userid,
                                                mentionsUsers=",".join(doc["mentions"]),
                                                mentionsRoles=",".join(doc["role_mentions"]),
                                                time=t)
                    writer.commit()
                    self.log("committed {0}\n".format(file))
                    writer = self.ix.writer()
                    for i in range(0,5):
                        try:
                            os.remove(path)
                            break
                        except:
                            pass
                    self.searchers = []
                    self.getSearcher()
                else:
                    time.sleep(10)

            except Exception as e:
                print(str(e))
                self.log(str(e))
                try:
                    if path:
                        if not os.path.isdir(self.failedDir):
                            os.mkdir(self.failedDir)
                        shutil.move(path, os.path.join(self.failedDir, file))
                except Exception as ee:
                    print(str(ee))
                    self.log(str(ee))
                    raise


    class ScopedSearcher:
        def __init__(self, parent, **kwargs):
            self.parent = parent
            self.handle = None
            self.args = kwargs
            self.time = time.time()

        def __enter__(self):
            try:
                self.handle = self.parent.searchers.pop()
                if (time.time() - self.handle.time) > 60:
                    self.handle = self.handle.refresh()
                    setattr(self.handle, 'time', time.time())
                    self.parent.log("Refreshed handle")
                return self.handle
            except:
                self.handle = self.parent.ix.searcher(**self.args)
                setattr(self.handle, 'time', time.time())
                return self.handle
        
        def __exit__(self,a,b,c):
            self.parent.searchers.append(self.handle)
            self.handle = None

    def getSearcher(self, **kwargs):
        return Index.ScopedSearcher(self, **kwargs)

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
                    results = self.query(text, max*(2+attempt), user, expand=(expand or (attempt > 0)), timer=t, dedupe=True)
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

            return Results(results)

    def query(self, text, max = 3, user = None, expand=False, userNames=[], dedupe=False, timer=Timer("index.query")):
        """ text: the main text query of the content. expand=bool applies to this. 
                  if user or userNames are supplied, text is restricted to content (else no field res)
            user: id of a user to restrict to
            userNames: ORed with 'user', but a text search in content :/
                  """
        with timer.sub_timer("query") as ot:
            with self.getSearcher(weighting = whoosh.scoring.TF_IDF) as searcher:
                with ot.sub_timer("inner-q") as t:
                    with t.sub_timer("query-parse") as s:
                        if expand:
                            qp = QueryParser("content", schema=self.ix.schema, termclass=whoosh.query.Variations)
                        else:
                            qp = QueryParser("content", schema=self.ix.schema)
                        nonExpandQP = QueryParser("content", schema=self.ix.schema)

                        userNodes = []
                        # Massive spaghetti here
                        textNode = qp.parse(text)
                        textNode.fieldname = "content"
                        if user:
                            userNode = whoosh.query.Term("user", user)
                            userNodes.append(userNode)
                        if userNames:
                            q2 = nonExpandQP.parse(" OR " .join(userNames))
                            q2.field = "content"
                            userNodes.append(q2)
                        q = textNode
                        if userNodes:
                            u = whoosh.query.Or(userNodes)
                            q = whoosh.query.And([q, u])
                    
                    with t.sub_timer("searcher.search") as s:
                        results = searcher.search(q, limit=max)

                    return deduper(results, dedupe=dedupe)

    async def collect_terms(self, t, usernames, corpusThresh, freq, minScore):
        with self.getSearcher() as s:
            ret = []
            q = whoosh.query.Term("content", t)
            uq = whoosh.query.Or([whoosh.query.Term("user", u) for u in usernames])
            qry = whoosh.query.And([q, uq])
            res = s.search(qry, groupedby="user")
            res.estimated_length()
            d = res.groups("user")
            for u,ary in d.items():
                if len(ary) > corpusThresh * freq:
                    score = 1000000* len(ary) / self.getCounts(u) / freq
                    if score > minScore:
                        ret.append((u, t, score))
                        break
            return ret
    async def terms_async(self, usernames, corpusThresh = 0.6, corpusNorm = False, minScore = 450):
        ret = []
        totalCounts = {u:self.getCounts(u) for u in usernames}
        num = re.compile(r"^\d+$")
        reader = self.ix.reader()
        numDocs = reader.doc_count()
        for t in reader.field_terms("content"):
            if num.match(t):
                continue
            if len(t) < 3:
                continue
            
            freq = reader.doc_frequency("content", t)
            if freq > 50 and freq < numDocs/100:
                ret += await self.collect_terms(t, usernames, corpusThresh, freq, minScore)
        return ret

    def terms(self, usernames, corpusThresh = 0.6, corpusNorm = False, minScore = 450):
        ret = []
        totalCounts = {u:self.getCounts(u) for u in usernames}
        num = re.compile(r"^\d+$")
        reader = self.ix.reader()
        numDocs = reader.doc_count()

        for t in reader.field_terms("content"):
            if num.match(t):
                continue
            if len(t) < 3:
                continue
            freq = reader.doc_frequency("content", t)
            if freq > 50 and freq < numDocs/100:
              #  print("{0}: {1}".format(t, freq))
                with self.getSearcher() as s:
                    q = whoosh.query.Term("content", t)
                    uq = whoosh.query.Or([whoosh.query.Term("user", u) for u in usernames])
                    qry = whoosh.query.And([q, uq])
                    res = s.search(qry, groupedby="user")
                    res.estimated_length()
                    d = res.groups("user")
                    for u,ary in d.items():
                        if len(ary) > corpusThresh * freq:
                            score = 1000000* len(ary) / totalCounts[u] / freq
                            if score > minScore:
                                ret.append((u, t, score))
                                break
        return ret

    def whoMentions(self, target, names):
        if type(names) != set:
            names = set(names)
        with self.getSearcher() as s:
            q = whoosh.query.Or([whoosh.query.Term("content", n) for n in names])
            uq = whoosh.query.Term("mentionsUsers", target)
            qry = whoosh.query.Or([q, uq])
            res = s.search(qry, limit=10000000)

            counts = defaultdict(int)
            for r in res:
                counts[r["user"]] += 1

            return counts

    def getTimes(self, userId):
        import whoosh.sorting
        from datetime import datetime, timedelta

        uq = whoosh.query.Term("user", userId)

        end = datetime.utcnow()
        end = datetime(end.year, end.month, end.day)
        gap = timedelta(hours=6)
        start = end - 180*gap

        facet = whoosh.sorting.DateRangeFacet("time", start, end, gap)
        with self.getSearcher() as s:
            r = s.search(uq, groupedby=facet)

        g = r.groups()

        return g

        


def getBestTerms(index, userNames):
    userIdNames = {v:k for k,v in userNames.items()}
    terms = index.terms({"182074044772909056": "Ina"}, corpusThresh = 0, corpusNorm=True, minScore = 0)
    userTerms = defaultdict(list)
    for t in terms:
        userTerms[t[0]].append(t)
    with open("terms.out", "w") as of:
        for uid,t in userTerms.items():
            t = sorted(t, key=lambda x:-x[2])
            try:
                of.write("Important words for {0}:\n".format(userNames.get(uid, "?")))
            except:
                continue
            for tup in t:
                try:
                    of.write("\t{0} (score: {1})".format(tup[1], int(tup[2])))
                    of.write("\n")
                except:
                    pass
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
if __name__ == "__main__":
    index = Index("./data/196373421834240000/index", start = False)
    with open("authors", encoding="utf-8") as f:
        users = json.loads( f.read())

    userNames = {v:k for k,v in users.items()}

    res = index.getTimes(userNames["Chaeldar"])
    counts = [(r[0], len(vals)) for r, vals in res.items() if r]

    totals = defaultdict(lambda:[0,0])

    for c in counts:
        key = c[0].weekday() + 0.25 * int(c[0].hour/6)
        totals[key][0] += c[1]
        totals[key][1] += 1

    averages = sorted([ (k,v[0]/v[1]) for k,v in totals.items()], key = lambda x : x[0] )
    groupedAverages = []
    for v in averages:
        day = int(v[0])
        part = int((v[0] % 1) * 4)

        while len(groupedAverages) <= day:
            groupedAverages.append([0,0,0,0])

        groupedAverages[day][part] = v[1]
    print ("day       : am1, am2, pm1, pm2")
    for i,v in enumerate(groupedAverages):
        print("{0: <10}: {1}, {2}, {3}, {4}".format(days[i], int(v[0]), int(v[1]), int(v[2]), int(v[3])))

    counts = sorted(counts, key=lambda x: x[0])
    with open("times.dat", "w") as of:
        for tup in counts:
            try:
                d = tup[0]
                #datetime.datetime.
                date = "{0}/{1}/{2} ({3})".format(d.day, d.month, d.year, d.weekday()+1)
                of.write("{0}:{1}\n".format(date, tup[1]))
            except:
                pass
    import sys
    sys.exit(0)

    #res = index.whoMentions(userNames["Jerka"], ["Jer", "Jerka"])
    res = index.whoMentions(userNames["Yuna"], ["Paula", "Yuna", "Yunai"])

    for u,count in res.items():
        try:
            print ("{0}: {1}".format( users[u], count ))
        except:
            pass

    while True:
        query = input("query:")
        results = index.query(query)
        for i,r in enumerate(results):
            try:
                if i > 10:
                    break
                print(r)
            except:
                pass