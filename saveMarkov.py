import re
import os
import sys
import markovify
import shutil
import markov 

sourceDir = "160_test_3" # lines dumped from discord dump
destDir = "corpus_3" # destination for markov data

if not os.path.isdir(destDir):
    os.mkdir(destDir)
skip = re.compile(r"^\[\d+:\d+ [aApP][mM]\]")
for file in os.listdir(sourceDir):
    try:
        path = os.path.join(sourceDir, file)
        with open(path, "rb") as f:
            bytestext = f.read()
            text = bytestext.decode("utf-8")
            text2 = ""
            for line in text.splitlines():
                line = line.strip() 
                if skip.match(line):
                    continue
                if line:
                    if text2:
                        text2 += " "
                    text2 += line
                    text2 += "."
            
            chain = markov.Text(text2, state_size=2)

            with open(os.path.join(destDir, file), "w") as of:
                of.write(chain.to_json())
    except Exception as e:
        print ("Failed on {0}".format(file))

shutil.copyfile("authors", os.path.join(destDir, "authors"))