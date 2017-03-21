import spacy

nlp = None
def filter(results, keyword):
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
                verbs.append(word)
        
        sub_verbs = []

        for word in doc:
            if word.dep_ == "nsubj":
                if word.lemma_ == keyword:
                    if word.head.pos_ == "VERB":
                        sub_verbs.append( (word, word.head) )

        if sub_verbs:  
            beg = sub_verbs[0][1].left_edge.idx 
            end = sub_verbs[0][1].right_edge.idx +  len(sub_verbs[0][1].right_edge.text)
            phrase = res[1][beg: end]
            


            ret.append((res[0], phrase))

    return ret
