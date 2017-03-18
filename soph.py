import json
import os
import re
import markov
import importlib
import discord
import time
import asyncio
import index

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

    def makeQuery(self, text):
        text = text.strip()
        if text[-1] == '?':
            text = text[0:-1]
        return text

    def __init__(self, corpus = None):
        self.client = None
        self.corpus = corpus
        self.index = None

    def setClient(self, _client):
        self.client = _client 

    async def consume(self, message):
        fromUser = message.author.display_name
        
        if fromUser == "Soph":
            return None

        payload = re.sub(Soph.addressPat, "", message.content)
        server = None
        if message.channel and hasattr(message.channel ,'server'):
            server = message.channel.server
        
        if message.channel.type != discord.ChannelType.private:
            if len(payload) == len(message.content):
                return None
            if message.channel.name == "ch160":
                return None

        if payload.startswith("who talks about"):
            reloaded = reload(index, "index.py")
            if reloaded or not self.index:
                self.index = index.Index("index")
            userIds = json.loads(open("authors").read())
            self.index.setUsers(userIds)
            query = payload[len("who talks about"):]
            query = self.makeQuery(query)
            results = self.index.queryStats(query)
            if len(results) > 10:
                results = results[:10]
            return "\n".join(["{0}: {1}".format(v[1], v[0]) for v in results])

        if payload.startswith("impersonate "):
            reloaded = reload(markov, "markov.py")
            if reloaded or not self.corpus:
                print ("Loading corpus")
                self.corpus = markov.Corpus("./corpus_3")
                print ("Loaded corpus")
            payload = re.sub("impersonate", "", payload)
            names = re.split(",", payload.strip())
            names = [name.strip() for name in names]
            try:
                lines = self.corpus.impersonate(names, 1)
                if lines:
                    reply = await self.stripMentions(lines[0], server)
                    return reply
                return "Hmm... I couldn't think of anything to say {0}".format(g_Lann)
            except Exception as e:
                print (e)
                return g_Lann

        if fromUser == "fLux":
            return "Lux, pls. :sweat_drops:"

        reply = await self.stripMentions(payload, server)
        return "I was addressed, and {0} said \"{1}\"".format(fromUser, reply)

    async def stripMentions(self, text, server = None):
        matches = re.search("<@[!&]*(\d+)>", text)
        if matches:
            for m in matches.groups():
                if server:
                    info = discord.utils.find(lambda x: x.id == m, server.members) or discord.utils.find(lambda x: x.id == m, server.roles)
                else:
                    info = await self.client.get_user_info(m)
                name = getattr(info, "display_name", getattr(info, "name", g_Lann))
                text = re.sub("<@[!&]*"+m+">", "@"+name, text)
        return text