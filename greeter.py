# -*- coding: utf-8 -*-
import re
import random
import json

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
    def __init__(self, helloList = None):
        defaultList = set([r"((good )?(morning|nighty?))",
            r"hi+",
            r"h?ello+",
            r"heya?",
            r"hiya+",
            r"hai+"])

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


def randomEmoji():
    global emoji
    index = random.randint(0,len(emoji)-1)
    return emoji[index]



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
        "hi Lux",
        "hi Lux <a>",
        "hi <1234>",
        "hi ??",
        "howdy"

        ]
    for line in lines:
        print (line)
        g = Greeter(["Howdy"])
        print (g.checkGreeting(line))
