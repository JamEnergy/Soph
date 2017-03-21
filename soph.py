import json
import os
import re
import markov
import importlib
import discord
import time
import asyncio
import index
import subject

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

class StartsWithChecker:
    def __init__(self, prefix):
        self.prefix = prefix

    def __call__(self, text):
        if text.startswith(self.prefix):
            return len(self.prefix)
        return -1

    def help(self):
        return "{0} <text>".format(self.prefix)

class PrefixNameSuffixChecker:
    def __init__(self, prefix, suffix):
        self.prefix = prefix
        self.suffix = suffix
        patString = "^\\s*{0} (.*) {1}".format(prefix, suffix)
        self.pat = re.compile(patString)

    def __call__(self, text):
        match = g_whatSaidPat.finditer(text)
        for m in match:
            off = m.start(1)
            return off
        return -1

    def help(self):
        return "{0} <name> {1} <text>".format(self.prefix, self.suffix)

g_whatSaidPat = re.compile(r"^\s*what did (.*) say about ")
def whatDidTheySayCheck(text):
    match = g_whatSaidPat.finditer(text)
    for m in match:
        off = m.start(1)
        return off
    return -1
    

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
        self.lastReply = 0
        self.lastFrom = ""
        # callback checkers should return -1 for "not this action" or offset of payload
        self.callbacks = [(StartsWithChecker("who talks about"), Soph.respondQueryStats),
                            (StartsWithChecker("who mentions"), Soph.respondMentions),
                            (StartsWithChecker("impersonate"), Soph.respondImpersonate),
                            (StartsWithChecker("who said"), Soph.respondWhoSaid),
                            (StartsWithChecker("what do we think of"), Soph.whatDoWeThinkOf),
                            (StartsWithChecker("what do we think about"), Soph.whatDoWeThinkOf),                            
                            (PrefixNameSuffixChecker("what did", "say about"), Soph.respondUserSaidWhat),
                            (StartsWithChecker("help"), Soph.help)] 

    async def help(self, prefix, suffix, message):
        ret = "I can parse requests of the following forms:\n"
        ret += "\n".join([c[0].help() for c in self.callbacks])
        return ret

    async def dispatch(self, payload, message):
        for c in self.callbacks:
            offset = c[0](payload)
            if offset != -1:
                resp = await c[1](self, payload[:offset], payload[offset:], message)
                if resp:
                    return resp
        return None

    def reloadIndex(self):
        """ reloads Index if necessary """
        reloaded = reload(index, "index.py")
        if reloaded or not self.index:
            self.index = index.Index("index")

    def loadUsers(self):
        """ return a map of userId -> userName """
        userIds = json.loads(open("authors").read())
        return userIds

    async def whatDoWeThinkOf(self, prefix, suffix, message):
        self.reloadIndex()
        reload(subject, "subject.py")
        userIds = self.loadUsers()
        self.index.setUsers(userIds)
        # TODO: Strip mentions

        ret = ""

        query = suffix
        query = self.makeQuery(query)

        results = self.index.queryLong(query, max=300)
        results = subject.filter(results, query.split(" ")[0]) or subject.filter(results, query.split(" ")[-1])
        if len(results) > 5:
            results = results[:5]
        ret +=  "We think...\n" + "\n".join( ["{0}: {1}".format(userIds[r[0]], r[1]) for r in results ] )

        return ret
        

    async def respondQueryStats(self, prefix, suffix, message):
        fromUser = message.author.display_name
        self.reloadIndex()
        userIds = self.loadUsers()
        self.index.setUsers(userIds)

        query = suffix
        query = self.makeQuery(query)
        results = self.index.queryStats(query)

        if len(results) > 10:
            results = results[:10]
        if not results:
            return "No one, apparently, {0}".format(fromUser)
        return "\n".join(["{0}: {1}".format(userIds[v[1]], v[0]) for v in results])

    async def respondMentions(self, prefix, suffix, message):
        fromUser = message.author.display_name
        self.reloadIndex()
        userIds = self.loadUsers()
        query = suffix
        for k, v in userIds.items():
            query = query.replace(v, k)
        query = self.makeQuery(query)
        results = self.index.queryStats(query)
        if len(results) > 10:
            results = results[:10]
        if not results:
            return "No one, apparently, {0}".format(fromUser)
        return "\n".join(["{0}: {1}".format(userIds[v[1]], v[0]) for v in results])

    async def respondWhoSaid(self, prefix, suffix, message):
        fromUser = message.author.display_name
        self.reloadIndex()
        userIds = self.loadUsers()
        query = suffix
        query = self.makeQuery(query)
        results = self.index.queryLong(query)
        if not results:
            return "Apparently no one, {0}".format(fromUser)
        return "\n".join(["{0}: {1}".format(userIds[r[0]], r[1]) for r in results])

    async def respondUserSaidWhat(self, prefix, suffix, message):
        fromUser = message.author.display_name
        server = getattr(message.channel, "server")
        self.reloadIndex()
        userNames = {v:k for k,v in self.loadUsers().items()}
        sayPat = re.compile(r"\s+say about\s")
        match = sayPat.finditer(suffix)
        for m in match:
            name = suffix[:m.start(0)].strip()
            user = userNames.get(name, None)
            if not user:
                if name == "Soph":
                    return "I can't tell you that."
                return "I don't know who {0} is {1}".format(name, g_Lann)
            payload = self.makeQuery(suffix[m.end(0):])

            ret = ""

            results = self.index.queryLong(payload, user = user, max= 5)
            if results:
                payload = re.sub(r'\*', r'', payload)
                resp = "*{0} on {1}*:\n".format(name, payload)
                for i in range(0,len(results)):
                    text = results[i][1]
                    if server:
                        text =  await self.stripMentions(text, server)
                    resp += "{0}) {1}\n".format(i+1, text)
                ret += resp
            if ret:
                return ret
        return "Nothing, apparently, {0}".format(fromUser)

    async def respondImpersonate(self, prefix, suffix, message):
        reloaded = reload(markov, "markov.py")
        if reloaded or not self.corpus:
            print ("Loading corpus")
            self.corpus = markov.Corpus("./corpus_3")
            print ("Loaded corpus")

        names = re.split(",", suffix.strip())
        names = [name.strip() for name in names]

        try:
            lines = self.corpus.impersonate(names, 1)
            if lines:
                reply = lines[0]
                if message.channel.type != discord.ChannelType.private:
                    reply = await self.stripMentions(reply, message.channel.server)
                return reply
            return "Hmm... I couldn't think of anything to say {0}".format(g_Lann)
        except Exception as e:
            print (e)
            return g_Lann

    def setClient(self, _client):
        self.client = _client 

    async def consume(self, message):
        fromUser = message.author.display_name
        if fromUser == "Soph":
            return None
            
        response = await self.consumeInternal(message)
        now = int(time.time())
        
        if (fromUser != self.lastFrom) and (now - self.lastReply < 2) and response and not (fromUser in response):
            response =  message.author.display_name + " - " + response

        self.lastReply = now
        self.lastFrom = fromUser
        return response

    async def consumeInternal(self, message):
        fromUser = message.author.display_name

        payload = re.sub(Soph.addressPat, "", message.content)
        server = None
        if message.channel and hasattr(message.channel ,'server'):
            server = message.channel.server

        
        if message.channel.type != discord.ChannelType.private:
            if len(payload) == len(message.content):
                return None
            if message.channel.name == "ch160":
                return None

        if not payload:
            return "What?"

        x = await self.dispatch(payload, message)
        if x:
            return x

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