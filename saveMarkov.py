import re
import os
import sys
import markovify
import shutil


sourceDir = "160_test_3"
destDir = "corpus"

MyText("thank you thank you :)", state_size=2)


if not os.path.isdir(destDir):
    os.mkdir(destDir)

for file in os.listdir(sourceDir):
    try:
        path = os.path.join(sourceDir, file)
        with open(path, "rb") as f:
            bytestext = f.read()
            text = bytestext.decode("utf-8").lower()
            text2 = ""
            for line in text.splitlines():
                line = line.strip() 
                if line:
                    if text2:
                        text2 += " "
                    text2 += line
                    text2 += "."
            
            chain = MyText(text2, state_size=2)

            with open(os.path.join(destDir, file), "w") as of:
                of.write(chain.to_json())
    except Exception as e:
        print ("Failed on {0}".format(file))

shutil.copyfile("authors", os.path.join(destDir, "authors"))