import json
import re
import index
import subject
from sophLogger import SophLogger
from timer import Timer
import question


def stripMentions(text, userNames):
    it = re.finditer("<?@[!&]*(\d+)>", text) # the <? is to account for trimming bugs elsewhere Dx
    userIds = {v:k for k,v in userNames.items()}
    for matches in it:
        for m in matches.groups():
            name = userIds.get(m, "?")
            if name:
                text = re.sub("<?@[!&]*"+m+">", "@"+name, text)
    return text

class TextEngine:
    def __init__(self, opts):
        self.log = SophLogger("textEngine.log")
        self.options = opts
        self.dir = opts.get("dir", "index")
        self.start = opts.get("startIndexing", False)
        self.maxResults = int(opts.get("maxResults", 150))
        self.index = index.Index(self.dir, start = self.start)
        self.qp = question.DumbQuestionParser()     
    
    #async def respondWhoVerb(self, prefix, suffix, message, want_bool=False, timer=NoTimer()):
    def answer(self, qtext, users = {}):
        """ Find lines that answer the question 'who verbs?'
            users should be a map of userName -> userIds
        """
        timer = Timer("Answer")

        userIds = {v:k for k,v in users.items()}

        pq = self.qp.parse(qtext, users)

        i_results = []

        restrictUser = None
        thisUserNames = None
        doFilter = True
        if pq.subject_type == question.SubjectTypes.User:
            restrictUser = users[pq.subject_val]
            thisUserNames = [re.escape(k) for k,v in users.items() if v == restrictUser]
            thisUserNames.append(restrictUser)

        if pq.subject_type == question.SubjectTypes.We:
            #thisUserNames = [k for k,v in users.items()]
            pass
        
        if pq.subject_type == question.SubjectTypes.Author:
            raise KeyError("Doh")

        predicates = set()
        objectIsSubject = False
        if pq.verb:
            if pq.verb.lemma_ == "say":
                doFilter=False
            elif pq.verb.lemma_ == "think" and pq.objects:
                objectIsSubject = True
            else:
                predicates.add(pq.verb.text)
        for o in pq.objects:
            if o.is_digit:
                predicates.add("({0} OR +{0})".format(o.text))
            else:
                predicates.add(o.text)
        if pq.other_obj_words:
            predicates.update([o.lemma_ for o in pq.other_obj_words])
        subjectId = None
        if pq.subject_val:
            subjectId = users.get(pq.subject_val, None)

        searchtext = " AND ".join(predicates)

        with timer.sub_timer("combined-query") as t:
            res = self.index.query(searchtext, self.maxResults, restrictUser, expand=True, userNames=thisUserNames, dedupe=True, timer=t)
            
        want_bool = False
        any_subj = False
        pred = None
        filteredResults = []
        if objectIsSubject:
            subjects = [o.lemma_ for o in pq.objects]
            want_bool = True # we allow "subject verb" for "what do we think"
        else:
            if pq.subject_type == question.SubjectTypes.We:
                subjects = [k for k,v in users.items()] + ["we"]
            elif pq.subject_type == question.SubjectTypes.User:
                subjects = [k for k,v in users.items() if v == subjectId]
            
            pred = pq.verb.lemma_

            if pq.objects:
                pred = pred +" " +  " ".join([o.lemma_ for o in pq.objects])        

            if pq.question_word:
                if pq.question_word.lemma_ == "who":
                    subjects = [k for k,v in users.items()]
                    any_subj = True
            else:
                want_bool = True

        with timer.sub_timer("subject-filter") as t:
            for r in res:
                if len(filteredResults) >= 10:
                    break
                try:
                    if not doFilter:
                        filteredResults.append(r)
                        continue
                    doc = stripMentions(r[1], users)
                    allow_i = False
                    if (pq.subject_type == question.SubjectTypes.We or any_subj) and not objectIsSubject:
                        allow_i = True
                    elif pq.subject_type == question.SubjectTypes.User and not objectIsSubject:
                        allow_i = (r[0] == subjectId)
                    # author subj not impl
                    
                    output = subject.checkVerbFull(doc, subjects, pred, want_bool, timer=t, subj_i = allow_i)
                    if output:
                        filteredResults.append((r[0],output["extract"]))
                except Exception as e:
                    self.log("Exception while doing NLP filter: {0}".format(e))     
        if filteredResults:
            return filteredResults
        return None
    
if __name__ == "__main__":
    opts = { "dir": r"data\196373421834240000\index"}
    te = TextEngine(opts)
    with open(r"C:\script\Soph\authors") as f:
        users = json.loads(f.read())
        userNames = {v:k for k,v in users.items()}
        userNames["Marta"] = userNames["Chaeldar"]
    while True:
        
        for inp in ["what does Pom think about Japan?", "what do we think about Japan?", "what did we say about Nexon?", "what do we think of Nexon?"]:        
            #inp = input("Ask a question:\n")
            results = te.answer(inp, userNames)
            try:
                print (results)
            except:
                pass