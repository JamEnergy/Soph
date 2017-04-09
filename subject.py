import spacy
from spacy.symbols import nsubj, VERB
from timer import * 
from nlp import nlp

def hasChildInSet(tok, objSet):
    try:
        for c in tok.children:
            if c.lemma_ in objSet:
                return True
    except:
        return False
    return False

def pipe(texts, batch_size=10, n_threads = 4):
    return nlp.pipe(texts)

def isSame(text1, text2):
    try:
        iter1 = nlp(text1)
        iter2 = nlp(text2)

        return [t.lemma for t in iter1] == [t.lemma for t in iter2]
    except:
        return False
def checkVerb(text, name, verb, want_bool, timer=NoTimer()):
    if name:
        subjects = [name]
    else:
        subjects = None
    return checkVerbFull(text, subjects, verb, want_bool, timer, subj_i = (not name))

def checkVerbFull(text, subjects, verb, want_bool, timer=NoTimer(), subj_i = False):
    """ subj_i: if True, allow 'i' as a subject """    
    output = {}
    require_object = False
    objects = set([])
    if verb:
        iter = nlp(verb)
        verb = iter[0]
        require_object = len(iter) > 1 or not want_bool
        
        if require_object and len(iter) > 1:
            for word in iter[1:]:
                objects.add(word.lemma_)
        objects = set(objects)

    if subjects:
        subjects = set ([name.lower().strip() for name in subjects])
    
    with timer.sub_timer("nlp") as t:
        if isinstance(text, str):
            doc = nlp(text.strip())
        else:
            doc = text
    if len(doc) > 3:
        output["full_text"] = doc.string
        s = ["{0} [{1} {3}]".format(word.text, word.lemma_, word.tag_, word.pos_) for word in doc]
        output["tokenized"] =  ", ".join(s)

        # Finding a verb with a subject from below — good
        verbs = set()
        for possible_subject in doc:
            if possible_subject.dep == nsubj and possible_subject.head.pos == VERB:
                if not verb or possible_subject.head.lemma_ == verb.lemma_:
                    verbs.add(possible_subject.head)

        # verbs with the correct things on the RHS?
        filtered_verbs = []

        for v in verbs:
            has_subj = False
            for l in v.lefts:
                if (subjects and l.lemma_ in subjects) or (subj_i and l.lower_ == "i"):
                    if want_bool and not require_object:
                        filtered_verbs.append(v)
                        has_subj = True
                        # do we break here?
                        break
                    elif objects and list(v.rights):
                        for r in v.rights:
                            if r.lemma_ in objects or hasChildInSet(r, objects):
                                filtered_verbs.append(v)
                                has_subj = True
                                break                        
                    elif require_object and list(v.rights):
                        for r in v.rights:
                            if r.pos_ == "NOUN" or "obj" in r.dep_:
                                filtered_verbs.append(v)
                                has_subj = True
                                break
            if (not has_subj) and subj_i: # TODO - this is too generous, ie, need to filter on not objects/require_object
                if v.text.endswith("ed") and v.dep_ == "ROOT":
                    filtered_verbs.append(v)

        for v in filtered_verbs:
            for left in v.subtree:
                if left.pos_ !="ADP":
                    break
            output["verb"] = v.lemma_
            beg = left.idx
            end = v.right_edge.idx+len(v.right_edge.text)
            output["extract"]=doc.string[beg:end]

        if "extract" in output:
            return output
        return None

def filter(results, keyword, max = 100):
    """ filters out results where the keyword isn't the subject?"""
    keyLemmas = set([w.lemma_ for w in nlp(keyword)])

    ret = []
    for res in results:
        r = res[1]
        doc = nlp(r)
        words = []
        sub_verbs = []

        for word in doc:
            if word.dep_ == "nsubj":
                if word.lemma_ in keyLemmas:
                    if word.head.pos_ == "VERB":
                        v = word.head
                        if list(v.rights) or not v.lemma_ == "be":
                            sub_verbs.append( (word, v) )

        if sub_verbs:  
            beg = sub_verbs[0][1].left_edge.idx 
            end = sub_verbs[0][1].right_edge.idx +  len(sub_verbs[0][1].right_edge.text)
            phrase = res[1][beg: end]
            
            ret.append((res[0], phrase))
            if len(ret) >= max:
                return ret

    return ret
