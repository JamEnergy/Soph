import json
import os
import re
import markov
import importlib
import discord
import time


async def dump(message):
    path = message.author.display_name + ".txt"
    if not os.path.exists(path):
        with open(path, "w") as of:
            async for log in client.logs_from(message.channel, limit=100):
                of.write(log.content)
                of.write("\n")
#   if not os.path.exists("jer.txt"):
async def dumpChannel(channel, dir):
    if not os.path.isdir(dir):
        os.mkdir(dir)
    fileHandles = {}
    authors = {}
    if os.path.exists("authors"):
        with open("authors") as f:
            authors = json.loads(f.read())
    i = 0
    lim = 1000000
    async for log in client.logs_from(channel, limit=lim):
        i = i+1
        if (i%500) == 0:
            with open("log.log", "w") as of:
                of.write ("{0}%".format(i/lim * 100))
        author = log.author.id
        if not author in fileHandles:
            authors[log.author.id] = log.author.display_name
            fileHandles[author] = open(os.path.join(dir, author), "ab")
            with open ("authors", "w") as of:
                of.write(json.dumps(authors, indent=4))

        fh = fileHandles[author]
        fh.write(log.content.encode("utf-8"))
        fh.write("\n".encode("utf-8"))

g_now = time.time()
g_modTimes = {}
def reload(module, filepath):
    """ reload module based on modified time of filepath"""
    global g_modTimes
    global g_now
    if not filepath in g_modTimes:
        g_modTimes[filepath] = g_now

    modTime = os.path.getmtime(filepath) 
    if modTime > g_modTimes[filepath]:
         g_modTimes[filepath] = modTime
         importlib.reload(module)
         return True

    return False
g_Lann = '<:lann:275432680533917697>'
class Soph:
    addressPat = re.compile(r"^Ok((,\s*)|(\s+))Soph\s*[,-\.:]\s*")

    def __init__(self, corpus = None):
        self.client = None
        self.corpus = corpus

    def setClient(self, _client):
        self.client = _client 

    async def consume(self, message):
        fromUser = message.author.display_name
        
        if fromUser == "Soph":
            return None

        payload = re.sub(Soph.addressPat, "", message.content)
        
        if message.channel.type != discord.ChannelType.private:
            if len(payload) == len(message.content):
                return None
            if message.channel.name == "ch160":
                return None

        if fromUser == "fLux":
            return "Lux, pls. :sweat_drops:"

        if payload.startswith("impersonate "):
            reloaded = reload(markov, "markov.py")
            if reloaded or not self.corpus:
                print ("Loading corpus")
                self.corpus = markov.Corpus("./corpus")
                print ("Loaded corpus")
            payload = re.sub("impersonate", "", payload)
            names = re.split(",", payload.strip())
            names = [name.strip() for name in names]
            try:
                lines = self.corpus.impersonate(names, 1)
                if lines:
                    return lines[0]
                return "Hmm... I couldn't think of anything to say {0}".format(g_Lann)
            except:
                return g_Lann

        
        return "I was addressed, and {0} said \"{1}\"".format(fromUser,payload)
