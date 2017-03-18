import markovify
import json
import random
import os
import re
from collections import OrderedDict

class Text(markovify.Text):
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
    def __init__(self, dir, filter=[]):
        authorsPath = os.path.join(dir, "authors")
        with open(authorsPath) as f:
            self.authorIds = json.loads(f.read())
            self.authors = {v:k for k,v in self.authorIds.items()}
        self.models = {}

        for file in os.listdir(dir):
            if file == "authors":
                continue
            if filter and not self.authorIds[file] in filter:
                continue

            path = os.path.join(dir, file)
            with open(path) as f:
                try:
                    contents = f.read()
                    self.models[file] = Text.from_json(contents)
                except:
                    print ("Failed on {0}".format(file))
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

    def impersonate(self, names, count=10):
        models = [self.models[self.authors[name]] for name in names]

        if len(models) == 1:
            model = models[0]
        else:
            model = markovify.combine(models, [1]*len(models))
        ret = []
        while len(ret) < count:
            sen = model.make_short_sentence(140)
            if sen:
                ret.append(Corpus.correctSentence(sen))
        return ret 
    def inventConversation(self, names, count=10):
            models = [self.models[self.authors[name]] for name in names]
            ret = []
            
            while len(ret) < count:
                i = random.randint(0,len(models)-1)
                s = models[i].make_short_sentence(140)
                if s:
                    s = Corpus.correctSentence(s)
                    ret.append( "{0}: {1}".format(names[i], s))
            return ret

if __name__ == "__main__":

    corp = Corpus("./corpus", filter=["Jerka", "Lisa"])
    lines = corp.impersonate(["Jerka"])
    for line in lines:
        print (line)

    lines = corp.inventConversation(["Jerka", "Lisa"])
    for line in lines:
        print (line)
