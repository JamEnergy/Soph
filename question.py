import spacy
import nlp
import re
from spacy.symbols import nsubj, VERB
from enum import Enum

class Targets (Enum):
    Bool = 0
    User = 1
    Any = 2
    NoTarget = 3

class SubjectTypes (Enum):
    User = 1
    We = 2
    Author = 3
class Question:
    def __init__(self, subject_type = None, 
                subject_val = None, 
                requires_object = True, 
                target_type = None, 
                objects = None, 
                verb = None, 
                text = None, 
                parse = None, 
                question_word = None, 
                other_obj_words = None):
        """ requires_object - set to True for "what does X eat" questions 
             subject_type is either Question.User or Question.We 
             subject_val is None for We, or a users 
             objects is a list of object words (no synonyms) 
             verb is a single word
             other_obj_words is a list of keywords that should be in the answer (describing the object)
             """
        
        self.requires_object = requires_object 
        self.subject_type = subject_type
        self.subject_val = subject_val
        self.target_type = target_type
        self.objects = objects or set()
        self.verb = verb 
        self.text = text
        self.parse = parse 
        self.question_word = question_word 
        self.other_obj_words = other_obj_words or set()

    def string(self):
        retLines = []
        if self.text:
            retLines.append("Text: {0}".format(self.text))

        if self.question_word:
            retLines.append("Qword: {0}".format(self.question_word))
        retLines.append("Subj type: {0}".format(self.subject_type))
        if self.subject_val:
            retLines.append("Subj: {0}".format(self.subject_val))
        if self.verb:
            retLines.append("Verb: {0}".format(self.verb.lemma_))
        if self.objects:
            retLines.append("Objects: {0}".format( ",".join([o.lemma_ for o in self.objects])))
        if self.other_obj_words:
            retLines.append("Other keywords: {0}".format(",".join([o.lemma_ for o in self.other_obj_words])))

        return "\n".join(retLines)
        
def printParse(gen):
    x = list(gen)
    disp = " ".join(["[{0}: {1}]".format(word, word.dep_) for word in x])
    return disp

class DumbQuestionParser:
    replNames = ["John", "James", "Paula", 'Aleksandr', 'Ayrton', 'Iverson']

    def __init__(self):
        self.nlp = nlp.nlp

    def parse(self, question, users):
        """ users should be a dict of userName -> id """

        ret = Question()
        pat = "|".join([r"(\b{0}\b)".format(re.escape(u)) for u in users])
        m = re.search(pat, question)
        cleanQuestion = question

        replName = "Xoxox"
        for r in DumbQuestionParser.replNames:
            if r not in users and r.lower() not in question.lower():
                replName = r # This is to deal with fuckers with spaces in their names
                break
        subject = None
        foundSubject = False
        subjectUser = None
        it = None
        nameToken = None
        mainVerb = None
        cleanQuestion = question
        if m: # we may have a subject
            user = m.group(0)
            loc = m.regs[0]
            question_prefix = question[0:loc[0]]
            predicate = question[loc[1]:]
            cleanQuestion = question_prefix + replName + predicate
            
            passedSubj = False
            it = self.nlp(cleanQuestion)

            i = 0
            verbIsNext = False
            for word in it:
                if word.pos == 94: # punct
                    continue
                if verbIsNext and not mainVerb:
                    mainVerb = word
                    verbIsNext = False
                if word.text == replName:
                    nameToken = word
                    verbIsNext = True
                elif word.pos == VERB and i > 0:
                    if not mainVerb or mainVerb.dep_ == "aux":
                        mainVerb = word
                i += 1

            if mainVerb:
                if mainVerb.idx < nameToken.idx: # main verb is before name... what?
                    nameTokenn = None

                if mainVerb.idx > nameToken.idx: # normal casce
                    ret.subject_type = SubjectTypes.User
                    ret.subject_val = user
                    foundSubject = True

        if not foundSubject:
            cleanQuestion = question # reset the question, kill the repl shit
            it = self.nlp(cleanQuestion)                    

        qwords = set(["who", "what", "how", "when", "where"])
        i = 0
        subjectIsNext = False
        backupObjects = set()
        passedMainVerb = False

        

        for word in it:
            if word.pos == 94: # punct
                continue

            if i == 0:
                if word.lemma_ in qwords:
                    ret.question_word = word
            if i > 0 and i < 3:
                if not ret.subject_type and  "sub" in word.dep_:
                    if word.lemma_ == "we":
                        ret.subject_type = SubjectTypes.We
            if i > 2:
                if word.dep_ in ["pobj", "dobj", "npadvmod"]:
                    ret.objects.add(word)
                elif word.dep_ in ["amod", "acl", "pcomp"]:
                    ret.other_obj_words.add(word)
            if i > 1 or (i > 0 and not foundSubject):
                if word.pos == VERB and (not mainVerb or mainVerb.dep_ == "aux"):
                    mainVerb = word
                    backupObjects = set()
            if mainVerb and word.idx > mainVerb.idx and word.is_alpha:
                backupObjects.add(word)
            i += 1

        if backupObjects and not ret.objects:
            ret.objects = set(backupObjects)
            ret.other_obj_words = []

        if mainVerb:
            ret.verb = mainVerb

        ret.parse = it
        ret.text = question
    
        return ret

class QuestionParser:
    replNames = ["John", "James", "Paula", 'Aleksandr', 'Ayrton', 'Iverson']

    def __init__(self):
        self.nlp = nlp.nlp

    def parse(self, question, users):
        """ users should be a dict of userName -> id """
        pat = "|".join([r"(\b{0}\b)".format(re.escape(u)) for u in users])
        m = re.search(pat, question)
        cleanQuestion = question

        replName = "Xoxox"
        for r in QuestionParser.replNames:
            if r not in users and r.lower() not in question.lower():
                replName = r # This is to deal with fuckers with spaces in their names
                break
        subject = None
        subjectUser = None
        
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
                if "subj" in word.dep_:
                    subject = word
                    if word.text == replName and not subjectUser:
                        cleanQuestion = replQuestion
                        subjectUser = m.group(0)

        verb = None
        it = self.nlp(cleanQuestion)

        ret = []
        objects = []
        i = 0 
        other_kw = []
        qword = None
        for word in it:
            ret.append(word)
            if i == 0:
                if word.dep_ == "nsubj" or word.dep_ == "dobj":
                    qword = word
            if not subject and word.dep_ == "nsubj":
                subject = word
            if i > 0 and word.pos == VERB:
                verb = word
            if verb and i > 1:
                if word.dep_ in ["pobj", "dobj"]:
                    objects.append(word)
                elif word.dep_ in ["amod", "acl", "pcomp" ]:
                    other_kw.append(word)
            i += 1

        q = Question()
        q.text = question
        q.parse = it
        if subject:
            if subject.lemma_ == "we":
                q.subject_type = SubjectTypes.We
            if subject.lemma_ == "who":
                q.subject_type = SubjectTypes.User
            if subject.lemma_ == "i":
                q.subject_type = SubjectTypes.Author
        if subjectUser:
            q.subject_val = subjectUser
            q.subject_type = SubjectTypes.User
        if verb:
            q.verb = verb
        q.objects = objects
        q.other_obj_words = other_kw
        if qword:
            q.question_word = qword.lemma_
        return q

if __name__ == "__main__":
    qp = DumbQuestionParser()
    users = {"Marta":1, "Chaeldar":1, "Lisa":2}
    texts = ["who eats pizza?",
             "who does talk about Lisa?",
             "who talks about dog?",
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
             "what did Marta say about big dogs?",
             "what did Marta say about eating dogs?",
             "what does Lisa drink?",
             "what did Lisa drink?",
             "does Lisa drink?",
             "did Lisa drink?",
             "who drinks?",
             "who drinks Lisa?" ]

    texts2 = [ "what do we play?", "does Marta like Nexon?", "does Marta like nexon?", "does Marta like?", "what does Marta like?"]

    while True:          
        for text in texts2:
            #text = input("Ask a question:\n")
            try:
                if text:
                    question = qp.parse(text, users)

                    print(question.string())
                    print ("")
                    #disp = " ".join(["[{0}: {1}]".format(word, word.dep_) for word in ret])
                    #print (disp)
            except Exception as e:
                print(e)
        break