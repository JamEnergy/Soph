import wsClient
from sophLogger import SophLogger as logger
import random
import greeter
import collections
import reloader
import itertools
import json
import os
import re
import markov
import importlib
import discord
import time
import asyncio
import sys
from timer import Timer,NoTimer
import traceback
import timeutils
import utils
import reactor
import subprocess
import names

    
class ScopedStatus:
    def __init__(self, client, text):
        self.client = client
        self.text = text
        
    async def __aenter__(self):
        try:
            await self.client.change_presence(game = discord.Game(name=self.text))    
        except:
            pass

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self.client.change_presence(game = None, status=discord.Status.online)    
        except:
            pass

class AlwaysCallback:
    def __init__(self, helpMsg):
        self.helpMsg = helpMsg

    def __call__(self, text):
        return 0

    def help(self):
        return "<always: {0}>".format(self.helpMsg)

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
        match = self.pat.finditer(text)
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
    thinkingEmojis = ["🤔", "📖", "😦", "🙍", "🙄", "😣", "😴", "😫", "😕", "😔", "😒", "🤢","😳"]
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

    def __init__(self, corpus = None, client = None):
        # TODO: check dependencies
        self.client = client
        self.log = logger("Soph.log")
        self.userCache = {} #userId to userName
        self.userCacheTime = 0
        self.userNameCache = {} # userName to userId
        self.aliases = {} # map of un -> uid
        self.options = Soph.defaultOpts
        self.optTime = time.time() - 1

        self.corpus = corpus

        # stupid test
        self.name_managers = names.NameManagerBundle(self.client, True)

        def loadMarkov(key):
            return markov.Corpus(os.path.join("data", str(key), "markovData"))
        self.markovs = utils.SophDefaultDict(loadMarkov)
        
        self.lastReply = 0
        self.userIds = None

        self.tz = {} # map of uid -> timezone
        self.serverOpts = {} # keyed by server name
        self.serverMap = {}
        self.lastFrom = ""
        self.greeters = {}
        self.reactor = None
        self.addressPat = None 
        self.childProcs = []
        # callback checkers should return -1 for "not this action" or offset of payload
        self.noPrefixCallbacks = [
                (AlwaysCallback("reacts to certain messages"), Soph.respondReact),
                (AlwaysCallback("converts times to UTC"), Soph.respondTimeExt),
                (AlwaysCallback("reacts to certain greetings"), Soph.respondGreet)           
            ]
        self.callbacks = [  (StartsWithChecker("who said"), Soph.respondQueryStats),
                            (PrefixNameSuffixChecker("what does", "talk about"), Soph.respondUserTerms),
                            (StartsWithChecker("who mentions"), Soph.respondMentions),
                            (StartsWithChecker("help"), Soph.help),
                            (StartsWithChecker("impersonate"), Soph.respondImpersonate),
                            (StartsWithChecker("analyze"), Soph.respondAnalyze),
                            (StartsWithChecker("set alias"), Soph.setAlias),
                            (StartsWithChecker("set locale"), Soph.setTimeZone),
                            (AlwaysCallback("parses various simple questions"), Soph.testTextEngine),
                            (StartsWithChecker("who talks about"), Soph.respondQueryStats),
                            (StartsWithChecker("set"), Soph.setOption)] 
        self.ready = False
        if self.client.is_logged_in:
            self.onReady()

    def stop(self):
        if hasattr(self, "childProcs"):
            for proc in self.childProcs:
                subprocess.Popen("TASKKILL /F /PID {pid} /T".format(pid=proc.pid))

    def onReady(self):
        try:
            self.options = Soph.defaultOpts

            with open("options.json", "r", encoding="utf-8") as f:
                opts = json.loads(f.read(), encoding = "utf-8")
                self.options.update(opts)
        except Exception as e:
            self.log("Crap: {0}".format(e))
            return
			
        self.greeting = self.options.get("greeting", "I'm ready")
        self.optTime = time.time()

        self.loadUsers()
        self.loadAliases()
        self.loadTz()
        task = self.loadAllUsers()
        fut = asyncio.ensure_future(task)

        async def check_deps():
            try:
                resp = await wsClient.call(8888, "ping", "")
                print ("index already up")
            except:
                print ("index isn't up")
                kwargs = {}
                #if platform.system() == 'Windows':
                # from msdn [1]
                #CREATE_NEW_PROCESS_GROUP = 0x00000200  # note: could get it from subprocess
                #DETACHED_PROCESS = 0x00000008          # 0x8 | 0x200 == 0x208
                #kwargs.update(creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP) 
                sp = subprocess.Popen(["python", "indexBundle.py"],
                                        start_new_session = True,
                                        shell=True, stdin=None, 
                                        stdout=None, stderr=None,
                                        close_fds=True, **kwargs)
                self.childProcs.append( sp ) 
                

        task = check_deps()
        fut = asyncio.ensure_future(task)

        self.addressPat = re.compile(r"^(Ok|So)((,\s*)|(\s+))"+ self.options["name"]+ r"\s*[,-\.:]\s*")

        for server in self.client.servers or {}:
            self.serverMap[server.name] = server.id

        if "servers" in self.options:
            for server_opts in self.options["servers"]:
                try:
                    id = server_opts["id"]
                except:
                    name = server_opts.get("name")
                    id = self.serverMap[name]
                self.serverOpts[id] = server_opts

            for k, o in self.serverOpts.items():
                regs = o.get("infoRegs", [])
                o["infoRegs"] = [re.compile(r) for r in regs]

            self.reactor = reactor.Reactor(self.serverOpts)

        def make_greeter(server):
            return greeter.Greeter(self.serverOpts.get(server.id, {}).get("greetings", {}), server)

        self.greeters = utils.SophDefaultDict(make_greeter)
        self.ready = True

    async def testTextEngine(self, prefix, suffix, message, timer=NoTimer()):
        un = {}
        aliasMap = utils.SophDefaultDict(lambda x:list())
        for k,v in self.aliases.items():
            aliasMap[v].append(k)

        if hasattr(message, "server"):
            for m in message.server.members:
                un[m.display_name] = m.id
                un[m.name] = m.id
                for alias in aliasMap[m.id]:
                    un[alias] = m.id
        results = await wsClient.call(8888, message.server.id, "call", "answer", suffix, un)
        lines = []
        if not results:
            return "I couldn't get an answer for that..."
        for r in results:
            name = await self.resolveId(r[0], server=message.server)
            content = r[1].replace("\n", "\n\t")
            content = await self.stripMentions(content, message.server)
            if len(content) > 100:
                content = content[:100] + "..."
            lines.append("{0}: {1}".format(name, content))
        return "\n".join(lines)

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
        self.aliases[newName] = self.userNameCache[existingName]

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
                self.aliases = json.loads(f.read())

                for k,v in self.aliases.items():
                    self.userNameCache[k] = v
    
    def loadTz(self):
        tz = {}
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
            ret += "\n".join([c[0].help() for c in self.noPrefixCallbacks])
            ret += "\n"
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


    async def dispatch(self, payload, message, timer=NoTimer(), usePrefix = True):
        if usePrefix:
            cbs = self.callbacks
        else:
            cbs = self.noPrefixCallbacks

        for c in cbs:
            offset = c[0](payload)
            if offset != -1:
                try:
                    resp = await c[1](self, payload[:offset], payload[offset:].strip(), message, timer=timer)
                    if resp:
                        return resp
                except Exception as e:
                    self.log(e)
        return None

    def loadUsers(self):
        """ return a map of userId -> userName """
        AUTHORS_FILENAME = "authors"
        if os.path.isfile(AUTHORS_FILENAME):
            self.userIds = json.loads(open("authors").read())
            for un, uid in self.userIds.items():
                self.userNameCache[uid] = un
            self.userCache.update(self.userIds)
        else:
            with open(AUTHORS_FILENAME, "w") as of:
                json.dump({}, of)
        
        return self.userIds

    async def respondReact(self, prefix, suffix, message, timer=NoTimer()):
        if self.reactor:
            await self.reactor.react(message, self.client)
        return None

    async def respondQueryStats(self, prefix, suffix, message, timer=NoTimer()):
        with timer.sub_timer("query-stats-callback") as t:
            fromUser = message.author.display_name
            userIds = await self.loadAllUsers()

            query = suffix
            query = self.makeQuery(query)
            
            results = await wsClient.call(8888, message.server.id, "call", "termStats", query) 

            if len(results) > 10:
                results = results[:10]
            if not results:
                return "No one, apparently, {0}".format(fromUser)
            lines = []
            lines.append("{0:<18}: {1:<6} \t[{2}]".format("user", "count", "freq/1000 lines"))
            for v in results:
                name = await self.resolveId(v[1], message.server)
                c = v[2]
                lines.append("{0:<18}: {1:<6} \t[{2:.1f}]".format(name, v[0], 1000*v[0]/c))
            return "```" + "\n".join(lines) + "```"

    async def respondMentions(self, prefix, suffix, message, timer=NoTimer()):
        fromUser = message.author.display_name
        userIds = await self.loadAllUsers()
        query = suffix
        for k, v in userIds.items():
            query = query.replace(v, k)
        query = self.makeQuery(query)

        results = await wsClient.call(8888, message.server.id, "call", "termStats", query)

        if len(results) > 10:
            results = results[:10]
        if not results:
            return "No one, apparently, {0}".format(fromUser)
        return "\n".join(["{0}: {1}".format(userIds[v[1]], v[0]) for v in results])

    async def respondUserTerms(self, prefix, suffix, message, timer=NoTimer()):
        try:
            name = re.sub(" talk about\??", "", suffix).strip()
            uid = self.userNameCache[name]
            self.log("Getting terms")

            await self.client.add_reaction(message, "👍🏻")

            done = False
            async def thinking():
                try:
                    nums = list(range(len(Soph.thinkingEmojis)))
                    random.shuffle(nums)
                    for i in nums:
                        eee = Soph.thinkingEmojis[i]
                        await asyncio.sleep(10)
                        if not done:
                            try:
                                asyncio.ensure_future(self.client.add_reaction(message, eee))
                            except:
                                self.log("{0}th emoji was invalid".format(i))
                except:
                    pass
                return True

            asyncio.ensure_future( thinking() )

            try:
                terms = await wsClient.call(8888, message.server.id, "call", "userTerms", {uid:name}, corpusThresh = 0, minScore = 0)
            except:
                raise
            finally:
                done = True
   
            self.log("Got terms")
            userTerms = collections.defaultdict(list)
            self.log("Making list")
            for t in terms:
                userTerms[t[0]].append(t)
            ret = ""
            self.log("Collated {0} terms".format(len(terms)))
            for uid,t in userTerms.items():
                t = sorted(t, key=lambda x:-x[2])

                try:
                    ret += ("Important words for {0}:\n".format(name))
                except Exception as e:
                    self.log(e)
                for tup in t[:25]:
                    try:
                        ret += ("\t{0} (score: {1})".format(tup[1], int(tup[2])))
                        ret += ("\n")
                    except:
                        pass
            if ret:
                return "```" + ret + "```"
        except Exception as e:
            self.log(e)
        return None

    async def respondImpersonate(self, prefix, suffix, message, timer=NoTimer()):
        reloaded = reloader.reload(markov, "markov.py")
        sid = message.channel.server.id
        if reloaded or not sid in self.markovs:
            self.log ("Loading corpus")
            corpus = self.markovs[sid]
            self.log ("Loaded corpus")

        corpus = self.markovs[sid]

        names = re.split(",", suffix.strip())
        names = [name.strip() for name in names]
        try:
            ids = [self.userNameCache[name] for name in names]
        except KeyError as key:
            return "Data for {0} not found {1}".format(key, g_Lann)

        try:
            lines = corpus.impersonate(ids, 1)
            if lines:
                reply = lines[0]
                if message.channel.type != discord.ChannelType.private:
                    reply = await self.stripMentions(reply, message.channel.server)
                return reply
            return "Hmm... I couldn't think of anything to say {0}".format(g_Lann)
        except Exception as e:
            self.log(e)
            return g_Lann

    async def respondAnalyze(self, prefix, suffix, message:discord.Message, timer=NoTimer()):
        
        return "Not implemented yet"


    async def respondTime(self, message):
        """ returns None if this wasn't a 'time' thing """
        uid = message.author.id
        text = await self.stripMentions(message.content, message.server)
        timeStr = timeutils.findTime(text)
        if not timeStr:
            return None
        if ("my time" in text) or ("for me" in text):
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
        if re.search(re.escape(timeStr) + r"\s*(UTC)|(server.?time)", text, re.IGNORECASE):
            utcTime = timeutils.to_utc(timeStr, "Etc/UTC")
            return "({0} UTC is {1} from now)".format(timeStr, timeutils.offset_from_now(utcTime))

        if not Soph.timeZonepat.search(text):
            if uid in self.tz:
                try:
                    utcTime = timeutils.to_utc(timeStr, self.tz[uid])
                except:
                    return None
            return "@{0} - what time zone?".format(message.author.display_name)

    async def respondTimeExt(self, prefix, suffix, message, timer=NoTimer()):
        try:
            opts = self.serverOpts.get(message.server.id, {})

            if self.options["timehelp"]:
                thc = opts.get("timeHelpChannels", {})
                if thc.get(message.channel.name, False):
                    resp = await self.respondTime(message)
                    if resp:
                        return resp
        except Exception as e:
            pass
        return None

    async def respondGreet(self, prefix, suffix, message, timer=NoTimer()):
        try:
            server = message.server
            opts = self.serverOpts.get(server.id, {})
            if message.channel.name in opts.get("greetChannels", {}):
                g = self.greeters[server]
                await g.add_reactions(message, self.client)
        except Exception as e:
            pass

        return None

    async def consume(self, message):
        if not self.ready:
            return None

        if os.path.getmtime("options.json") > self.optTime:
            self.onReady()

        fromUser = message.author.display_name
        if message.author.id == self.client.user.id:
            return None
            
        with Timer("full_request") as t:
            if message.channel.type != discord.ChannelType.private:
                server = message.server
                        
            response = await self.consumeInternal(message, timer=t)
            now = int(time.time())
            
            if (fromUser != self.lastFrom) and (now - self.lastReply < 2) and response and not (fromUser in response):
                response =  message.author.display_name + " - \n" + response

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
            self.log (message.content[0:100])

            payload = re.sub(self.addressPat, "", message.content)
            server = None
            if message.channel and hasattr(message.channel ,'server'):
                server = message.channel.server

            x = await self.dispatch(payload, message, timer=timer, usePrefix = False)
            if x:
                return x

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

    async def resolveId(self, uid, server):
        return await self.name_managers.get(server).get_name(uid)

    async def stripMentions(self, text, server):
        it = re.finditer("<?@[!&]*(\d+)>", text) # the <? is to account for trimming bugs elsewhere Dx
        for matches in it:
            for m in matches.groups():
                name = await self.resolveId(m, server)
                if name:
                    text = re.sub("<?@[!&]*"+m+">", "@"+name, text)
        return text
