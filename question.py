import spacy
import re
from spacy.symbols import nsubj, VERB

class Question:
    User = 1
    We = 2
    def __init__(self, subject_type = Question.User, subject_val = None, requires_object = True):
        """ requires_object - set to True for "what does X eat" questions 
             subject_type is either Question.User or Question.We 
             subject_val is None for We, or a list of users """
        
        self.requires_object = requires_object 
        self.subject_type = subject_type

def printParse(gen):
    x = list(gen)
    disp = " ".join(["[{0}: {1}]".format(word, word.dep_) for word in x])
    return disp

class QuestionParser:
    def __init__(self):
        self.nlp = spacy.load('en')

    def parse(self, question, users):
        """ users should be a dict of userName -> id """
        pat = "|".join([r"(\b{0}\b)".format(u) for u in users])
        m = re.search(pat, question)
        cleanQuestion = question
        replName = "XXXX"
        if m:
            loc = m.regs[0]
            replQuestion = question[0:loc[0]] + replName + question[loc[1]:]
            replQuestion = replQuestion.strip()
            replQuestion = replQuestion[0].upper() + replQuestion[1:]
            
            verbs = set()
            it = self.nlp(replQuestion)
            it = list(it)
            for word in it:
                if word.dep == nsubj and word.head.pos == VERB:
                    verbs.add(word.head)
                if word.text == replName:
                    if "subj" in word.dep_:
                        cleanQuestion = replQuestion
                        break
        ret = []
        it = self.nlp(cleanQuestion)

        for word in it:
            ret.append(word)

        return ret

if __name__ == "__main__":
    qp = QuestionParser()
    users = {"Marta":1, "Chaeldar":1, "Lisa":2}
    texts = ["who talks about dog?",
             "who talks about Lisa?",
             "who mentions Lisa?",
             "what did we say about dog?",
             "what did we say about Lisa?",
             "what do we think about dog?",
             "what do we think about Lisa?",
             "what do we think of dogs?",
             "what do we think of Lisa?",
             "what did Marta say about Lisa?",
             "what did Marta say about dogs?",
             "what does Lisa drink?",
             "what did Lisa drink?",
             "does Lisa drink?",
             "did Lisa drink?",
             "who drinks?",
             "who drinks Lisa?" ]

    while True:          
        for text in texts:
            #text = input("Ask a question:\n")
            try:
                if text:
                    ret = qp.parse(text, users)
                    disp = " ".join(["[{0}: {1}]".format(word, word.dep_) for word in ret])
                    print (disp)
            except:
                pass