import re
import random
import json

pat = r"(((good )?(morning|nighty?))|hi+|h?ello+|heya?)\b(,?\s+(team|all|cakes?|friends))?(\s*<.*>)?(\s*[^a-zA-Z]+)?$"

pat = re.compile(pat, re.IGNORECASE)
emoji = []
try:
    with open("emoji.json", encoding = "utf-8") as f:
        emoji = json.loads( f.read() )
except Exception as e:
    print (e)

def randomEmoji():
    global emoji
    index = random.randint(0,len(emoji)-1)
    return emoji[index]


def checkGreeting(text):
    text = text.strip()
    m = pat.match(text)
    if m:
        return True

    return False

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
        "hi ??"

        ]
    for line in lines:
        print (line)
        print (checkGreeting(line))
