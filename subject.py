import spacy
from spacy.symbols import nsubj, VERB
nlp = None

def checkVerb(text, name, verb, want_bool):
    global nlp
    if not nlp:
        nlp = spacy.load('en')
    
    output = {}
    
    iter = nlp(verb)
    verb = iter[0]
    require_object = len(iter) > 1 or not want_bool
    
    if name:
        subject = name.lower().strip()
    else:
        subject = ""
    line = text.strip()

    doc = nlp(line)
    if len(doc) > 3:
        output["full_text"] = line
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
            output["extract"]=line[beg:end]

        if "extract" in output:
            return output
        return None








def filter(results, keyword):
    """ filters out results where the keyword isn't the subject?"""
    global nlp
    if not nlp:
        nlp = spacy.load('en')
    keyword = keyword.lower()
    keyword = nlp(keyword)[0].lemma_
    ret = []
    for res in results:
        r = res[1]
        doc = nlp(r)
        words = []
        verbs = []

        for word in doc:
            words.append( (word.lemma_, word.pos_) )
            if word.pos_ == "VERB":
                if len(list(word.rights)) or not word.lemma_ == "be":
                    verbs.append(word)
        
        sub_verbs = []

        for word in doc:
            if word.dep_ == "nsubj":
                if word.lemma_ == keyword:
                    if word.head.pos_ == "VERB":
                        v = word.head
                        if list(v.rights) or not v.lemma_ == "be":
                            sub_verbs.append( (word, v) )

        if sub_verbs:  
            beg = sub_verbs[0][1].left_edge.idx 
            end = sub_verbs[0][1].right_edge.idx +  len(sub_verbs[0][1].right_edge.text)
            phrase = res[1][beg: end]
            


            ret.append((res[0], phrase))

    return ret
