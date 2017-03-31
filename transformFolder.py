import json
import os
import sys
from collections import defaultdict

incomingDir = "incoming"
outDir = "userData"
try:
    os.mkdir(outDir)
except:
    pass

class FileHandles(dict):
    def __missing__(self, key):
        self[key] = open(os.path.join(outDir, key), "a", encoding = "utf-8")
        return self[key]

outfhs = FileHandles()

for file in os.listdir(incomingDir):
    path = os.path.join(incomingDir, file)
    infh = open(path, encoding="utf-8")
    for line in infh:
        doc = json.loads(line)
        outfh = outfhs[doc["user"]]
        outfh.write(doc["content"])
        outfh.write("\n")

    for uid,fh in outfhs.items():
        fh.flush()

print ("Finished")