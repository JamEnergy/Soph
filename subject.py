import spacy
from spacy.symbols import nsubj, VERB
from timer import * 
nlp = None

def pipe(texts, batch_size=10, n_threads = 4):
    global nlp
    if not nlp:
        nlp = spacy.load('en')

    return nlp.pipe(texts)

def isSame(text1, text2):
    global nlp
    if not nlp:
        nlp = spacy.load('en')
    try:
        iter1 = nlp(text1)
        iter2 = nlp(text2)

        return [t.lemma for t in iter1] == [t.lemma for t in iter2]
    except:
        return False

def checkVerb(text, name, verb, want_bool, timer=NoTimer()):
    global nlp
    if not nlp:
        nlp = spacy.load('en')
    
    output = {}
    
    iter = nlp(verb)
    verb = iter[0]
    require_object = len(iter) > 1 or not want_bool
    objects = []
    if require_object and len(iter) > 1:
        for word in iter[1:]:
            pass
    objects = set(objects)
    if name:
        subject = name.lower().strip()
    else:
        subject = ""

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
                if possible_subject.head.lemma_ == verb.lemma_:
                    verbs.add(possible_subject.head)

        filtered_verbs = []
        for v in verbs:
            for l in v.lefts:
                if (subject and l.lemma_ == subject.lower()) or (not subject and l.lower_ == "i"):
                    if want_bool and not require_object:
                        filtered_verbs.append(v)
                    elif require_object and list(v.rights):
                        for r in v.rights:
                            if r.pos_ == "NOUN":
                                filtered_verbs.append(v)
                                break

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
    global nlp
    if not nlp:
        nlp = spacy.load('en')
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
