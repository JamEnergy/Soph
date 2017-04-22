# A mixin kind of thing to hold the old functions
class LegacySoph:
    async def respondWhoSaid(self, prefix, suffix, message, timer=NoTimer()):
        fromUser = message.author.display_name
        server = getattr(message.channel,'server',None)
        userIds = await self.loadAllUsers()
        query = suffix
        query = self.makeQuery(query)
        with timer.sub_timer("query-long-wrap") as t:
            index = self.getIndex(message.server.id)
            results = index.queryLong(query, timer=t, max=10)
            results = [r for r in results if len(r[1]) < 300]
        if not results:
            return "Apparently nothing, {0}".format(fromUser)
        ret = "\n".join(["{0}: {1}".format(userIds.get(r[0], "?"), r[1]) for r in results])
        with timer.sub_timer("strip-mentions") as t:
            ret = await self.stripMentions(ret)
        return ret

    async def respondWhoVerb(self, prefix, suffix, message, want_bool=False, timer=NoTimer()):
        reloader.reload(subject, "subject.py")

        index = self.getIndex(message.channel.server.id)

        userIds = await self.loadAllUsers()
        i_results = []
        pred = self.makeQuery(suffix)

        userNames = [k for k,v in self.userNameCache.items()]
        with timer.sub_timer("combined-query") as t:
            res = index.query(pred, 100, None, expand=True, userNames=None, dedupe=True, timer=t)
        
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
        return "I'm not sure what {0} {1}s".format("who", pred)

    async def respondUserVerbObject(self, prefix, suffix, message, timer=NoTimer()):
        return await self.respondUserVerb(prefix, suffix, message, True, timer=timer)

    async def respondUserVerb(self, prefix, suffix, message, want_bool=False, timer=NoTimer()):
        reloader.reload(subject, "subject.py")

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
            index = self.getIndex(message.server.id)
            res = index.query(pred, 100, uid, expand=True, userNames=thisUserWords, dedupe=True, timer=t)
        
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
                        output = subject.checkVerbFull(doc, thisUserWords, pred, want_bool, timer=t)
                    if output:
                        filteredResults.append((r[0],output["extract"]))
                except:
                    pass             
        if filteredResults:
            return "\n".join(["{0}: {1}".format(userIds.get(r[0], r[0]),r[1]) for r in filteredResults])

        if " " in pred:
            return "I don't know"
        return "I'm not sure what {0} {1}s".format(subj, pred)


    async def respondSentimentUser(self, prefix, suffix, message, timer=NoTimer()):
        ret =[]
        
        unMap = {}
        aliasMap = utils.SophDefaultDict(lambda x:list())
        for k,v in self.aliases.items():
            aliasMap[v].append(k)

        if hasattr(message, "server"):
            for m in message.server.members:
                unMap[m.display_name] = m.id
                unMap[m.name] = m.id
                for alias in aliasMap[m.id]:
                    unMap[alias] = m.id

        for un,uid in unMap.items():
            if suffix.startswith(un):
                suffix = suffix[len(un):]
                suffix = suffix.strip()
                if suffix.startswith("on "):
                    suffix = suffix[3:]

                index = self.getIndex(message.server.id)
                if suffix:
                    results = index.query(suffix, max=50, user = uid, expand = True, dedupe=True)
                else:
                    results = index.getLast(uid, 50)

                contents = [r[1] for r in results]
                scores = sentiment.analyze(contents)
                for idx, score in enumerate(scores):
                    content = contents[idx]
                    score = score["aggregate"]["score"]
                    mag = abs(score)
                    if mag > 0.4:
                        ret.append((content, score))
                break
        if not ret:
            res = sentiment.analyze(suffix)
            agg = res[0]["aggregate"]
            return "Sounds {0} ({1:.2f})".format(agg["sentiment"], agg["score"])
        else:
            lines = []
            for r in ret[0:10]:
                if r[1] > 0:
                    sign = ":grinning:"
                else:
                    sign = ":slight_frown:"
                lines.append("{0}: {1} ({2:.2f})".format(r[0], sign, r[1]))
            return "\n".join(lines)


    async def whatDoWeThinkOf(self, prefix, suffix, message, timer=NoTimer()):
        with timer.sub_timer("reload") as t:
            
            reloader.reload(subject, "subject.py")
        
        userIds = await self.loadAllUsers()
        # TODO: Strip mentions

        ret = ""

        query = suffix
        query = self.makeQuery(query)
        index = self.getIndex(message.server.id)
        results = index.queryLong(query, max=300, timer=timer)
        with timer.sub_timer("subject-filter") as t:
            results = subject.filter(results, query, max=5)
            lines = []
            for r in results:
                un = await self.getUserName(r[0])
                text = await self.stripMentions(r[1])
                lines.append("{0}: {1}".format(un, text))
        ret +=  "We think...\n" + "\n".join( lines )

        return ret


    async def respondUserSaidWhat(self, prefix, suffix, message, timer=NoTimer()):
        fromUser = message.author.display_name
        server = getattr(message.channel, "server", None)
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
            index = self.getIndex(message.server.id)
            rgen = index.queryLong(payload, user = user, max= 20, expand=True, timer=timer)
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


    async def parse(self, prefix, suffix, message, timer=NoTimer()):
        import question
        un = {}
        aliasMap = utils.SophDefaultDict(list)
        for k,v in self.aliases.items():
            aliasMap[v].append(k)

        if hasattr(message, "server"):
            for m in message.server.members:
                un[m.display_name] = m.id
                un[m.name] = m.id
                for alias in aliasMap[m.id]:
                    un[alias] = m.id

        un.update(self.aliases)
        pq = self.qp.parse(suffix, un)
        return pq.string()