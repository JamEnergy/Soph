# -*- coding: utf-8 -*-
import re
import random
import json
import discord

with open("inputemoji.json", encoding="utf-8") as f:
    emojis = f.read()
    emojis = json.loads(emojis)
    helloEmojis = set(emojis)
helloEmojis.update(set(['<:hello:230475328265519104>']))
emoji = []
try:
    with open("emoji.json", encoding = "utf-8") as f:
        emoji = json.loads( f.read() )
except Exception as e:
    print (e)


class Greeter():
    def __init__(self, greetings_opts, server:discord.Server):
        global emoji
        self.server = server
        emojis = server.emojis
        self.emoji_lookup = {e.name: e for e in emojis}
        self.opts = greetings_opts
        defaults = greetings_opts.get("defaults", {})
        self.chance = defaults.get("chance", 0.5)
        self.emoji = emoji + defaults.get("emoji", [])
        helloList = defaults.get("greetings", [])
        defaultList = {r"((good )?(morning|nighty?))",
            r"hi+",
            r"h?ello+",
            r"heya?",
            r"hiya+",
            r"hai+"}

        if helloList:
            for h in helloList:
                defaultList.add(h)
        
        hellos = "|".join(defaultList)

        pat = r"({0})\b(,?\s+(team|all|cakes?|friends))?(\s*<.*>)?(\s*[^a-zA-Z]+)?$".format(hellos)
        self.pat = re.compile(pat, re.IGNORECASE)

    def checkGreeting(self, text):
        text = text.strip()
        global helloEmojis
        if text in helloEmojis:
            return True
        m = self.pat.match(text)
        if m:
            return True

        return False

    async def add_reactions(self, message:discord.Message, client):
        try:
            if self.checkGreeting(message.content):
                await client.add_reaction(message, "👋")

                this_user_settings = self.get_user_opts(message.author.id)
                this_chance = this_user_settings.get("chance", self.chance) # I want Penny

                # or to have her sit next to me while I work on Soph
                # she's very sweet and nice to me
                while random.random() < this_chance:
                    e = self.randomEmoji(message.author.id)
                    try:
                        await client.add_reaction(message, e)
                    except:
                        break
                else:
                    pass
        except Exception as e:
            pass

    def get_user_opts(self, author_id):
        user_settings = self.opts.get("users", {})
        this_user_settings = user_settings.get(author_id, {})
        return this_user_settings

    def randomEmoji(self, author_id):
        this_user_settings = self.get_user_opts(author_id)
        this_user_emoji = this_user_settings.get("emoji", [])

        index = random.randint(0,len(self.emoji)+len(this_user_emoji)-1)

        if index < len(self.emoji):
            return self.emoji[index]
        else:
            e = this_user_emoji[index-len(self.emoji)]
            return self.emoji_lookup.get(e, e)



if __name__ == "__main__":
    lines = [
        "Hi team",
        "Hey team",
        "Hello team",
        "ello team",
        "Heya team",
        "hey team",
        "ello team",
        "hi",
        "ello",
        "hi Penny",
        "hi Penny <a>",
        "hi <1234>",
        "hi ??",
        "howdy"

        ]
    for line in lines:
        print (line)
        g = Greeter(["Howdy"])
        print (g.checkGreeting(line))
