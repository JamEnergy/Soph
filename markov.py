import markovify
import json
import random
import os
import re

from utils import MRU



class Text(markovify.Text):
    sentenceEndPat = re.compile(r"[.?!]$")
    posPat = re.compile(r"_.*")

    def __init__(self, input_text, state_size=2, chain=None):
        """
        input_text: A string.
        state_size: An integer, indicating the number of words in the model's state.
        chain: A trained markovify.Chain instance for this text, if pre-processed.
        """
        self.input_text = input_text
        self.state_size = state_size
        runs = list(self.generate_corpus(input_text))

        # Rejoined text lets us assess the novelty of generated setences
        self.rejoined_text = self.sentence_join(map(self.word_join, runs))
        self.chain = chain or markovify.Chain(runs, state_size)

    def word_join(self, words):
        """
        Re-joins a list of words into a sentence.
        """
        ret = ""
        for word in words:
            if ret:
                ret += " "
            ret += Text.posPat.sub("", word)
        return ret

    def split_into_sentences(text):
        potential_end_pat = re.compile(r"".join([
            r"([\w\.'’&\]\)]+[\.\?!])", # A word that ends with punctuation
            r"([‘’“”'\"\)\]]*)", # Followed by optional quote/parens/etc
            r"(\s+(?![a-z\-–—]))", # Followed by whitespace + non-(lowercase or dash)
            ]), re.U)
        dot_iter = re.finditer(potential_end_pat, text)
        end_indices = [ (x.start() + len(x.group(1)) + len(x.group(2)))
            for x in dot_iter
            if markovify.splitters.is_sentence_ender(x.group(1)) ]
        spans = zip([None] + end_indices, end_indices + [None])
        sentences = [ text[start:end].strip() for start, end in spans ]
        return sentences or [text]

    def sentence_split(self, text):
        """
        Splits full-text string into a list of sentences.
        """
        return Text.split_into_sentences(text)

    def test_sentence_input(self, sentence):
        """
        A basic sentence filter. This one rejects sentences that contain
        the type of punctuation that would look strange on its own
        in a randomly-generated sentence. 
        """
        reject_pat = re.compile(r"(^')|('$)|\s'|'\s|[\"(\(\)\[\])]")
        # Decode unicode, mainly to normalize fancy quotation marks
        if sentence.__class__.__name__ == "str":
            decoded = sentence
        else:
            decoded = unidecode(sentence)
        # Sentence shouldn't contain problematic characters
        return True
        if re.search(reject_pat, decoded): return False
        return True

class Corpus:
    class ModelStore(dict):
        def __init__(self, _dir):
            self.dir = _dir
            super(Corpus.ModelStore, self).__init__()
            
        def __missing__(self, key):
            with open(os.path.join(self.dir, key)) as f:
                contents = f.read()
                new = Text.from_json(contents)
                self[key] = new
                return new

    def __init__(self, dir, filter=[]):
        self.dir = dir
        self.comboCache = MRU(3)
        self.models = Corpus.ModelStore(self.dir)

    def sentence_join(self, sentences):
        """
        Re-joins a list of sentences into the full text.
        """
        ret = ""
        for s in sentences:
            s = s.strip()
            terminated = sentenceEndPat.match(s[-1])
            if not terminated:
                s = s + "."
            if ret:
                ret += " "

            if self.correctCapitalization:
                s = self.correctSentence(s)
            ret += s
        return ret

    def correctSentence(text):
        letter = re.compile(r"\w")
        upper = True
        ret = ""
        for char in text:
            if char == '.':
                upper = True
            if upper and letter.match(char):
                ret += char.upper()
                upper = False
            else:
                ret  += char
        ret = re.sub(r"\bi\b", "I", ret)
        return ret

    def getCombinedModel(self, ids):
        key = "+".join(set(ids))
        model = self.comboCache.get(key)
        if not model:
            models = [self.models[uid] for uid in ids]
            model = markovify.combine(models, [1]*len(models))
            self.comboCache.insert(key, model)
        return model

    def impersonate(self, ids = [], count=10):
        if len(ids) == 1:
            model = self.models[ids[0]]
        else:
            model = self.getCombinedModel(ids)

        ret = []
        tries = 0
        while len(ret) < count:
            tries = tries+1
            if tries > 2 * count:
                break
            sen = model.make_short_sentence(300)
            if sen:
                #sen = Corpus.correctSentence(sen)
                ret.append(sen)
        return ret 

    def inventConversation(self, ids, count=10):
            models = [self.models[uid] for uid in ids]
            ret = []
            tries = 0
            while len(ret) < count:
                tries = tries+1
                if tries > 2 * count:
                    break
                i = random.randint(0,len(models)-1)
                s = models[i].make_short_sentence(140)
                if s:
                    #s = Corpus.correctSentence(s)
                    ret.append( "{0}: {1}".format(ids[i], s))
            return ret

if __name__ == "__main__":
    with open("authors", encoding="utf-8") as f:
        authordata = f.read()
        authors = json.loads(authordata)
        authorLookup = {v:k for k,v in authors.items()}
    corp = Corpus("./markovData2")
    lines = corp.impersonate([authorLookup["Lisa"]])
    for line in lines:
        print (line)

    lines = corp.inventConversation(["116294611550339080", "116294611550339080"])
    for line in lines:
        print (line)
