import re
import os
import sys
import markovify
import shutil
import markov 
import spacy
import transformFolder

logf = open ("markov.log", "w")
def log(text):
    try:
        logf.write(text)
        logf.write("\n")
        print(text)
    except:
        pass

nlp = spacy.load("en")


def makeMarkovs(sourceDir, destDir):
    if not os.path.isdir(destDir):
        os.mkdir(destDir)

    skip = re.compile(r"^\[\d+:\d+ [aApP][mM]\]")
    for file in os.listdir(sourceDir):
        try:
            path = os.path.join(sourceDir, file)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
                trainingLines = []
                text2 = ""
                for line in text.splitlines():
                    line = line.strip() 
                    if skip.match(line):
                        continue
                    if line:
                        line = line.replace("...", " ")
                        tokens = nlp(line)
                        try:
                            pass
                            #markov.Text(line, state_size=2)
                        except Exception as e:
                            log ("Can't tokenize line")
                            log (str(e))
                            log (line)
                        taggedLine = ""
                        for tok in tokens:                             
                            taggedLine += tok.text
                            if tok.pos_ != "PUNCT":
                                taggedLine += "_"
                                taggedLine += tok.pos_
                            if tok.string[-1] == " ":
                                taggedLine += " "

                        trainingLines.append(taggedLine.strip() + ".")
                text2 = ". ".join(trainingLines)
                chain = markov.Text(text2, state_size=2)

                with open(os.path.join(destDir, file), "w") as of:
                    of.write(chain.to_json())
        except Exception as e:
            print ("Failed on {0}".format(file))

    #shutil.copyfile("authors", os.path.join(destDir, "authors"))

if __name__ == "__main__":
    incomingDir = r"../data/219894896172072971/incoming"
    sourceDir = "tmp" 
    transformFolder.run(incomingDir, sourceDir)
    
    destDir = "markovData2_weebs" # destination for markov data
    makeMarkovs(sourceDir, destDir)#
    print("Ok, really finished")