import index
import subject
import reloader

class TextEngine:
    def __init__(self, opts):
        self.options = opts
        self.dir = opts.get("dir", "index")
        self.start = opts.get("startIndexing", False)
        self.index = index.Index(self.dir, start = start)

    def reloadIndex(self):
        """ reloads Index if necessary """
        reloaded = reloader.reload(index, "index.py")
        
        if reloaded or not self.index:
            self.index = index.Index(self.dir, start = self.start)
        return index        

    # TODO: Write a parser here!
    def makeQuery(self, text):
        """ removes ?mark"""
        text = text.strip()
        if text[-1] == '?':
            text = text[0:-1]
        return text
    
    #async def respondWhoVerb(self, prefix, suffix, message, want_bool=False, timer=NoTimer()):
    def answer(self, question, users):
        """ Find lines that answer the question 'who verbs?'
            users should be a map of userName -> userIds
        """
        #reloader.reload(subject, "subject.py")
        #index = self.reloadIndex()
        i_results = []
        pred = self.makeQuery(suffix)

        userNames = [k for k,v in self.userNameCache.items()]
        with timer.sub_timer("combined-query") as t:
            res = self.index.query(pred, 100, None, expand=True, userNames=None, dedupe=True, timer=t)
        
        filteredResults = []

        with timer.sub_timer("subject-filter") as t:
            for r in res:
                if len(filteredResults) >= 10:
                    break
                try:
                    doc = r[1]
                    output = subject.checkVerbFull(doc, userNames, pred, want_bool, timer=t, subj_i = True)
                    if output:
                        filteredResults.append((r[0],output["extract"]))
                except Exception as e:
                    self.log("Exception while doing NLP filter: {0}".format(e))     
        if filteredResults:
            return "\n".join(["{0}: {1}".format(userIds.get(r[0], r[0]),r[1]) for r in filteredResults])

        if " " in pred:
            return "I don't know"
        return "I'm not sure what {0} {1}s".format("who", pred)
    
