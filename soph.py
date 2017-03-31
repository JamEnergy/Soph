from sophLogger import SophLogger as logger
import itertools
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
import sys
from timer import Timer,NoTimer
import traceback
import timeutils


class ScopedStatus:
    def __init__(self, client, text):
        self.client = client
        self.text = text
        
    async def __aenter__(self):
        await self.client.change_presence(game = discord.Game(name=self.text))    

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.change_presence(game = None, status=discord.Status.online)    

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

class SplitChecker(StartsWithChecker):
    def __init__(self, prefix):
        StartsWithChecker.__init__(self, prefix)
    
    def help(self):
        return "{0} <user> <text>".format(self.prefix)

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
g_nickNamePat = re.compile(r"^\s*\((.*)\)\s*")
g_Lann = '<:lann:275432680533917697>'

class Soph:
    timeZonepat = re.compile(r"(CET)|(UTC)|(time)|(GMT)|(BST)|(CEST)|(server)", re.IGNORECASE)
    master_id = '178547716014473216'
    aliasPath = "aliases"
    defaultOpts = {"timing" : False, "timehelp":False, "index":False, "name":"Soph"}

    def makeQuery(self, text):
        """ removes ?mark"""
        text = text.strip()
        if text[-1] == '?':
            text = text[0:-1]
        return text

    async def getUserId(self, name):
        return self.userNameCache.get(name, None)
    
    async def getUserName(self, uid, server = None):
        if uid in self.userCache:
            return self.userCache[uid]

        info = await self.client.get_user_info(uid)
        if info:
            name = getattr(info, "display_name", None) or getattr(info, "name", g_Lann)
            self.userCache[uid] = name
            self.userNameCache[name] =uid
            return name
        
        return None

    async def loadAllUsers(self):
        """ load and return map of id->name """
        if time.time() - self.userCacheTime > 60:
            for server in self.client.servers:
                for member in server.members:
                    uid = member.id
                    self.userCache[uid] = member.display_name
                    self.userNameCache[member.display_name] = uid
                    self.userNameCache[member.name] = uid
            self.userCacheTime = time.time()
        return self.userCache

    def __init__(self, corpus = None):
        self.log = logger("Soph.log")
        self.userCache = {} #userId to userName
        self.userCacheTime = 0
        self.userNameCache = {} # userName to userId
        self.options = Soph.defaultOpts
        try:
            with open("options.json") as f:
                opts = json.loads(f.read())
                self.options.update(opts)
        except:
            pass
        self.client = None
        self.corpus = corpus
        self.index = None
        self.lastReply = 0
        self.userIds = None
        self.loadUsers()
        self.loadAliases()
        self.tz = {} # map of uid -> timezone
        self.loadTz()
        self.lastFrom = ""
        self.addressPat = re.compile(r"^(Ok|So)((,\s*)|(\s+))"+ self.options["name"]+ r"\s*[,-\.:]\s*")
        # callback checkers should return -1 for "not this action" or offset of payload
        self.callbacks = [(StartsWithChecker("who talks about"), Soph.respondQueryStats),
                            (StartsWithChecker("who said"), Soph.respondQueryStats),
                            (StartsWithChecker("who mentions"), Soph.respondMentions),
                            (StartsWithChecker("impersonate"), Soph.respondImpersonate),
                            (StartsWithChecker("what did we say about"), Soph.respondWhoSaid),
                            (StartsWithChecker("what do we think of"), Soph.whatDoWeThinkOf),
                            (StartsWithChecker("what do we think about"), Soph.whatDoWeThinkOf),                            
                            (PrefixNameSuffixChecker("what did", "say about"), Soph.respondUserSaidWhat),
                            (SplitChecker("what does"), Soph.respondUserVerb),
                            (SplitChecker("what did"), Soph.respondUserVerb),
                            (SplitChecker("does"), Soph.respondUserVerbObject),
                            (SplitChecker("did"), Soph.respondUserVerbObject),
                            (StartsWithChecker("who"), Soph.respondWhoVerb),
                            (StartsWithChecker("set alias"), Soph.setAlias),
                            (StartsWithChecker("set locale"), Soph.setTimeZone),
                            (StartsWithChecker("set"), Soph.setOption),
                            (StartsWithChecker("help"), Soph.help)] 

    async def setAlias(self, prefix, suffix, message, timer=NoTimer()):
        if message.author.id != Soph.master_id:
            return "You aren't allowed to touch my buttons :shy:"

        index = suffix.index("=")
        left = suffix[0:index].strip()
        right = suffix[index+1:].strip()

        await self.loadAllUsers()

        if left in self.userNameCache:
            existingName = left
            newName = right
        elif right in self.userNameCache:
            existingName = right
            newName = left
        else:
            return g_Lann

        if newName in self.userNameCache:
            canonicalName = self.userCache[self.userNameCache[newName]]
            if canonicalName == newName:
                newName = existingName
            return "{0} is already called {1} :/".format(canonicalName, newName)

        self.userNameCache[newName] = self.userNameCache[existingName]

        aliases = {}
        if os.path.exists(Soph.aliasPath):
            with open(Soph.aliasPath) as f:
                aliases = json.loads(f.read())
        aliases[newName] = self.userNameCache[newName]
        with open(Soph.aliasPath, "w") as f:
            f.write(json.dumps(aliases, indent=True))
        
        return "Done ({0} -> {1})".format(newName, existingName)
    
    def loadAliases(self):
        # map of names->ids
        if os.path.exists(Soph.aliasPath):
            with open(Soph.aliasPath) as f:
                aliases = json.loads(f.read())

                for k,v in aliases.items():
                    self.userNameCache[k] = v
    
    def loadTz(self):
        try:
            with open("timezones") as f:
               tz = json.loads( f.read() )
        except:
            if os.path.exists("timezones"):
                return g_Lann
        self.tz = tz

    async def setTimeZone(self, prefix, suffix, message, timer=NoTimer()):
        tz = suffix.strip()
        if "/" not in tz:
            tz = "Europe/"+tz
        try:
            timeutils.to_utc("00:00", tz)
        except:
            return "Tried to set your locale to {0}, but that doesn't work with time conversion".format(tz)
        self.tz[message.author.id] = tz
        with open("timezones", "w", encoding="utf-8") as of:
            of.write(json.dumps(self.tz, indent=True))
        return "Done"                    

    async def setOption(self, prefix, suffix, message, timer=NoTimer()):
        if message.author.id != Soph.master_id:
            return "You aren't allowed to touch my buttons :shy:"

        suffix = suffix.strip()
        index = suffix.index("=")
        key = suffix[0:index].strip()
        val = suffix[index+1:].strip()
        if val.lower() == "true":
            val = True
        elif val.lower() == "false":
            val = False
        self.options[key] = val

        if key == "markov":
            self.corpus = markov.Corpus(val)
        return "Done"

    async def help(self, prefix, suffix, message, timer=NoTimer()):
        suffix = suffix.strip()
        if not suffix:
            ret = "I can parse requests of the following forms:\n"
            ret += "\n".join([c[0].help() for c in self.callbacks])
            return ret
        elif suffix.startswith("timezones"):
            if message.channel.type != discord.ChannelType.private:
                return "Ask me in private :shy:"
            region = suffix[len("timezones"):]
            region = region.strip()
            
            with open ("all_timezones.json") as f:
                tzs = json.loads(f.read())            

            if not region:
                pat = re.compile(r'/.*')
                zones = set([pat.sub("", t) for t in tzs if "/" in t])
                return "Need a region to filter on, because there are loads.\nUse the command help timezones <region> with one of these regions:\n{0}".format("\n".join(zones))
            
            tzs = [re.sub(".*/", "", t) for t in tzs if t.lower().startswith(region.lower())]
                
            return "The supported locales in {0} are:\n".format(region) + "\n".join(tzs)
        return g_Lann


    async def dispatch(self, payload, message, timer=NoTimer()):
        for c in self.callbacks:
            offset = c[0](payload)
            if offset != -1:
                self.log (message.content[0:100])
                resp = await c[1](self, payload[:offset], payload[offset:].strip(), message, timer=timer)
                if resp:
                    return resp
        return None

    def reloadIndex(self):
        """ reloads Index if necessary """
        reloaded = reload(index, "index.py")
        
        if reloaded or not self.index:
            self.index = index.Index("index", start = self.options["index"])
        return index

    def loadUsers(self):
        """ return a map of userId -> userName """
        self.userIds = json.loads(open("authors").read())
        for un, uid in self.userIds.items():
            self.userNameCache[uid] = un
        self.userCache.update(self.userIds)
        
        return self.userIds

    async def respondWhoVerb(self, prefix, suffix, message, want_bool=False, timer=NoTimer()):
        reload(subject, "subject.py")
        index = self.reloadIndex()

        userIds = await self.loadAllUsers()
        i_results = []
        pred = self.makeQuery(suffix)

        userNames = [k for k,v in self.userNameCache.items()]
        with timer.sub_timer("combined-query") as t:
            res = self.index.query(pred, 100, None, expand=True, userNames=None, dedupe=True, timer=t)
        
        filteredResults = []

        with timer.sub_timer("subject-filter") as t:
            for r in res:
                if len(filteredResults) >= 10:
                    break
                try:
                    doc = r[1]
                    output = subject.checkVerbFull(doc, userNames, pred, want_bool, timer=t, subj_i = True)
                    if output:
                        filteredResults.append((r[0],output["extract"]))
                except Exception as e:
                    self.log("Exception while doing NLP filter: {0}".format(e))     
        if filteredResults:
            return "\n".join(["{0}: {1}".format(userIds.get(r[0], r[0]),r[1]) for r in filteredResults])

        if " " in pred:
            return "I don't know"
        return "I'm not sure what {0} {1}s".format(subj, pred)

    async def respondUserVerbObject(self, prefix, suffix, message, timer=NoTimer()):
        return await self.respondUserVerb(prefix, suffix, message, True, timer=timer)

    async def respondUserVerb(self, prefix, suffix, message, want_bool=False, timer=NoTimer()):
        reload(subject, "subject.py")
        index = self.reloadIndex()

        userIds = await self.loadAllUsers()
        userNames = self.userNameCache

        thisUserWords = []
        i_results = []

        for subj,uid in self.userNameCache.items():
            if suffix.startswith(subj) and suffix[len(subj)] == " ":
                pred = self.makeQuery(suffix[len(subj):].strip())
                nickNames = None
                thisUserWords = [uid]
                for _name, _id in self.userNameCache.items():
                    if _id == uid:
                        thisUserWords.append(_name)
                break

        with timer.sub_timer("combined-query") as t:
            res = self.index.query(pred, 100, uid, expand=True, userNames=thisUserWords, dedupe=True, timer=t)
        
        filteredResults = []

        with timer.sub_timer("subject-filter") as t:
            for r in res:
                if len(filteredResults) >= 10:
                    break
                try:
                    doc = r[1]
                    if uid == r[0]:
                        output = subject.checkVerb(doc, None, pred, want_bool, timer=t)
                    else:
                        for n in thisUserWords:
                            output = subject.checkVerb(doc,n , pred, want_bool, timer=t)
                            if output:
                                break
                    if output:
                        filteredResults.append((r[0],output["extract"]))
                except:
                    pass             
        if filteredResults:
            return "\n".join(["{0}: {1}".format(userIds.get(r[0], r[0]),r[1]) for r in filteredResults])

        if " " in pred:
            return "I don't know"
        return "I'm not sure what {0} {1}s".format(subj, pred)

    async def whatDoWeThinkOf(self, prefix, suffix, message, timer=NoTimer()):
        with timer.sub_timer("reload") as t:
            self.reloadIndex()
            reload(subject, "subject.py")
        
        userIds = await self.loadAllUsers()
        self.index.setUsers(userIds)
        # TODO: Strip mentions

        ret = ""

        query = suffix
        query = self.makeQuery(query)

        results = self.index.queryLong(query, max=300, timer=timer)
        with timer.sub_timer("subject-filter") as t:
            results = subject.filter(results, query, max=5)
            lines = []
            for r in results:
                un = await self.getUserName(r[0])
                text = await self.stripMentions(r[1])
                lines.append("{0}: {1}".format(un, text))
        ret +=  "We think...\n" + "\n".join( lines )

        return ret

    async def respondQueryStats(self, prefix, suffix, message, timer=NoTimer()):
        with timer.sub_timer("query-stats-callback") as t:
            fromUser = message.author.display_name
            with t.sub_timer("reload") as r:
                self.reloadIndex()
            userIds = await self.loadAllUsers()
            self.index.setUsers(userIds)

            query = suffix
            query = self.makeQuery(query)
            results = self.index.queryStats(query, expand=True, timer= t)

            if len(results) > 10:
                results = results[:10]
            if not results:
                return "No one, apparently, {0}".format(fromUser)
            return "\n".join(["{0}: {1}".format(userIds[v[1]], v[0]) for v in results])

    async def respondMentions(self, prefix, suffix, message, timer=NoTimer()):
        fromUser = message.author.display_name
        self.reloadIndex()
        userIds = await self.loadAllUsers()
        query = suffix
        for k, v in userIds.items():
            query = query.replace(v, k)
        query = self.makeQuery(query)
        results = self.index.queryStats(query) # TODO: do a proper mentions query...
        if len(results) > 10:
            results = results[:10]
        if not results:
            return "No one, apparently, {0}".format(fromUser)
        return "\n".join(["{0}: {1}".format(userIds[v[1]], v[0]) for v in results])

    async def respondWhoSaid(self, prefix, suffix, message, timer=NoTimer()):
        fromUser = message.author.display_name
        server = getattr(message.channel,'server',None)
        with timer.sub_timer("reload") as t:
            self.reloadIndex()
        userIds = await self.loadAllUsers()
        query = suffix
        query = self.makeQuery(query)
        with timer.sub_timer("query-long-wrap") as t:
            results = self.index.queryLong(query, timer=t, max=10)
            results = [r for r in results if len(r[1]) < 300]
        if not results:
            return "Apparently nothing, {0}".format(fromUser)
        ret = "\n".join(["{0}: {1}".format(userIds.get(r[0], "?"), r[1]) for r in results])
        with timer.sub_timer("strip-mentions") as t:
            ret = await self.stripMentions(ret)
        return ret
        

    async def respondUserSaidWhat(self, prefix, suffix, message, timer=NoTimer()):
        fromUser = message.author.display_name
        server = getattr(message.channel, "server", None)
        self.reloadIndex()
        await self.loadAllUsers()
        userNames = self.userNameCache
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

            rgen = self.index.queryLong(payload, user = user, max= 20, expand=True, timer=timer)
            results = []
            for r in rgen:
                if len(results) > 4:
                    break
                if len(r[1]) < 300 and not subject.isSame(r[1], payload):
                    results.append(r)
                    
            if results:
                payload = re.sub(r'\*', r'', payload)
                resp = "*{0} on {1}*:\n".format(name, payload)
                for i in range(0,len(results)):
                    text = results[i][1]
                    text =  await self.stripMentions(text, server)
                    resp += "{0}) {1}\n".format(i+1, text)
                ret += resp
            if ret:
                return ret
        return "Nothing, apparently, {0}".format(fromUser)

    async def respondImpersonate(self, prefix, suffix, message, timer=NoTimer()):
        reloaded = reload(markov, "markov.py")
        if reloaded or not self.corpus:
            self.log ("Loading corpus")
            self.corpus = markov.Corpus("./markovData")
            self.log ("Loaded corpus")

        names = re.split(",", suffix.strip())
        names = [name.strip() for name in names]
        try:
            ids = [self.userNameCache[name] for name in names]
        except KeyError as key:
            return "Data for {0} not found {1}".format(key, g_Lann)

        try:
            lines = self.corpus.impersonate(ids, 1)
            if lines:
                reply = lines[0]
                if message.channel.type != discord.ChannelType.private:
                    reply = await self.stripMentions(reply, message.channel.server)
                return reply
            return "Hmm... I couldn't think of anything to say {0}".format(g_Lann)
        except Exception as e:
            self.log (e)
            return g_Lann

    def setClient(self, _client):
        self.client = _client 

    async def respondTime(self, message):
        """ returns None if this wasn't a 'time' thing """
        uid = message.author.id
        text = await self.stripMentions(message.content)
        timeStr = timeutils.findTime(text)
        if timeStr and ( ("my time" in text) or ("for me" in text)):
            if uid in self.tz:
                try:
                    utcTime = timeutils.to_utc(timeStr, self.tz[uid])
                except:
                    return None
                utcTimeStr = str(utcTime)[:-3]
                tzStr = re.sub(".*/", "", self.tz[uid])
                return "{0} for {1} ({2}) is {3} UTC ({4} from now)".format(timeStr, message.author.display_name, tzStr, utcTimeStr, timeutils.offset_from_now(utcTime))
            else:
                return "{0}, please register your timezone in bot channel with \"Ok Soph, set locale <Continent/City>\" ".format(message.author.display_name)
            
        if timeStr and not Soph.timeZonepat.search(text):
            if uid in self.tz:
                try:
                    utcTime = timeutils.to_utc(timeStr, self.tz[uid])
                except:
                    return "I tried to convert {0} to UTC, but I couldn't figure it out... {1}".format(timeStr, g_Lann)
            return "@{0} - what time zone?".format(message.author.display_name)

    async def consume(self, message):
        fromUser = message.author.display_name
        if message.author.id == self.client.user.id:
            return None
        
        with Timer("full_request") as t:
            if self.options["timehelp"]:
                if message.channel.name == "numanuma"  or message.channel.name == "botchannel":
                    resp = await self.respondTime(message)
                    if resp:
                        return resp
            
            response = await self.consumeInternal(message, timer=t)
            now = int(time.time())
            
            if (fromUser != self.lastFrom) and (now - self.lastReply < 2) and response and not (fromUser in response):
                response =  message.author.display_name + " - " + response

            self.lastReply = now
            self.lastFrom = fromUser
            if not response:
                t.disable()
            
        if self.options["timing"] and response:
            response += "\n{0:.2f}s".format(t.duration)
        
        return response

    async def consumeInternal(self, message, timer=NoTimer()):
        async with ScopedStatus(self.client, "with your text data") as status:
            fromUser = message.author.display_name

            payload = re.sub(self.addressPat, "", message.content)
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

            x = await self.dispatch(payload, message, timer=timer)
            if x:
                return x

            if fromUser == "fLux":
                return "Lux, pls. :sweat_drops:"
                
            reply = await self.stripMentions(payload, server)
            return "I was addressed, and {0} said \"{1}\"".format(fromUser, reply)

    async def stripMentions(self, text, server = None):
        it = re.finditer("<?@[!&]*(\d+)>", text) # the <? is to account for trimming bugs elsewhere Dx
        for matches in it:
            for m in matches.groups():
                name = "?"
                try:
                    name = await self.getUserName(m, server)
                    if not name:
                        if server:
                            info = discord.utils.find(lambda x: x.id == m, server.roles)
                        else:
                            info = await self.client.get_user_info(m)
                        name = getattr(info, "display_name", getattr(info, "name", g_Lann))
                except:
                    pass
                if name:
                    text = re.sub("<?@[!&]*"+m+">", "@"+name, text)
        return text