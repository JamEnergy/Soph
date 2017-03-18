import discord
import importlib
import soph
import os
import json 
client = discord.Client()

tok = open("token.dat").read()
dumpDir = "some_test"
async def dumpChannel(client, channel, dir):
    if not os.path.isdir(dir):
        os.mkdir(dir)
    fileHandles = {}
    authors = {}
    if os.path.exists("authors"):
        with open("authors") as f:
            j = f.read()
            if j:
                authors = json.loads(j)
    i = 0
    lim = 1000000
    async for log in client.logs_from(channel, limit=lim):
        i = i+1
        if (i%500) == 0:
            for k,v in fileHandles.items():
                v.flush()
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

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    channels = client.get_all_channels()
    for channel in channels:
        if channel.type == discord.ChannelType.text:
            if channel.name in ["ch160", "numanuma", "potatogallery", "gamelounge", "lisasworkshop", "norisworkshop", "rant"]:
                await dumpChannel(client, channel, dumpDir)

client.run(tok)
