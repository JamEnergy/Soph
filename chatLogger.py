from sophLogger import SophLogger as Logger
import discord
import asyncio
import re
import time
import importlib
import os
import json 
import datetime
from collections import defaultdict
client = discord.Client()
import shutil
import utils
skip = re.compile(r"(^\[\d+:\d+ [aApP][mM]\])|(.*((Today)|(Yesterday)) at \d+:\d+ [AP]M)|(.* - \d\d/\d\d/20\d\d\s*$)")

_log = Logger("chatlog.log")
def log_text(text):
    _log(text)

tok = open("token.dat").read()

async def dumpChannel(client, channel, dir, disableLinks, fromTime = None, toTime = None):
    tempDir = "temp"
    utils.ensureDirs(tempDir)
    utils.ensureDirs(dir)
    
    log_text ("dumping {0}\n".format(channel.name))

    authors = {}
    if os.path.exists("authors"):
        with open("authors") as f:
            j = f.read()
            if j:
                authors = json.loads(j)
    i = 0
    lim = 10000000
    gen = client.logs_from(channel, limit=lim, after=fromTime, before=toTime)
    minLen = 20
    maxLen = 100
    gap = 5

    userDocs = defaultdict( lambda x:  { "content" : "",
                    "role_mentions" : set([]),
                    "mentions" : set([]),
                    "timestamp" : None,
                    "user" : x
            })
    try:
        fh = None
        filename = ""
        numSkipped = 0
        async for log in gen:
            i = i+1
            if (i%2500) == 0:
                fh.close()
                shutil.move(path, os.path.join(dir, filename))
                fh = None
                log_text ("{0} messages...\n".format(i))

            if not fh:
                filename = "{0}".format(datetime.datetime.utcnow().timestamp())
                path = os.path.join(tempDir, filename)
                fh = open(path, "wb")

            author = log.author.id
            if author == client.user.id:
                continue
            content = log.content
            if skip.match(content):
                log_text("skipping {0}".format(content[0:200]))
                numSkipped += 1
                continue

            if log.embeds and disableLinks:
                content = re.sub("http", "xxx", content)

            doc = { "content" : content,
                    "role_mentions" : set(log.raw_role_mentions),
                    "mentions" : set(log.raw_mentions),
                    "timestamp" : log.timestamp.timestamp(),
                    "user" : author
            }

            if author in userDocs:
                thisDoc = userDocs[author]
                old = (doc["timestamp"] - thisDoc["timestamp"] > gap)
                newTooLong = (len(doc["content"]) + len(thisDoc["content"])) > minLen
                if old or newTooLong: #flush oldDoc
                    thisDoc["mentions"] = list(thisDoc["mentions"])
                    thisDoc["role_mentions"] = list(thisDoc["role_mentions"])
                    try:
                        j = json.dumps(thisDoc)
                        fh.write(j.encode("utf-8"))
                        fh.write("\n".encode("utf-8"))
                    except:
                        log_text("couldn't write {0}".format(thisDoc["content"]))
                    del userDocs[author]

            if not author in userDocs:
                userDocs[author] = doc
            else:
                thisDoc = userDocs[author]
                thisDoc["content"] = thisDoc["content"] + "..." + doc["content"]
                thisDoc["mentions"].update(doc["mentions"])
                thisDoc["role_mentions"].update(doc["role_mentions"])

        for k, v in userDocs.items():
            v["mentions"] = list(v["mentions"])
            v["role_mentions"] = list(v["role_mentions"])
            try:
                j = json.dumps(v)
                fh.write(j.encode("utf-8"))
                fh.write("\n".encode("utf-8"))
            except:
                log_text("couldn't write {0}".format(v["content"]))
    except Exception as e:
        log_text (e)
    if fh:
        fh.close()
        shutil.move(path, os.path.join(dir, filename))
    log_text("Messages: {0}, of which skipped: {1}".format(i, numSkipped))
    log_text ("Finished channel\n")

@client.event
async def on_ready():
    log_text('Logged in as')
    log_text(client.user.name)
    log_text(client.user.id)
    log_text('------')

    
    
    while True:        
        with open("options.json") as f:
            options = json.loads(f.read())

        baseDir = options.get("indexesBase","data")

        for s in client.servers:
            serverDir = os.path.join(baseDir, s.id)
            
            svrOpts = None
            for it in options["servers"]:
                if it.get("name", -1) == s.name or it.get("id", -1) == s.id:
                    svrOpts = it
                    break
            if not svrOpts:
                log_text("No config entry for {0} ({1}), skipping this server".format(s.name, s.id))
                continue
        
            log_text ("Dumping {0}...\n".format(s.name))

            lastRun = None
            timeFile = os.path.join(serverDir, "last_run.time")
            
            if os.path.exists(timeFile):
                with open(timeFile, "r") as f:
                    t = f.read()
                    lastRun = float(t)
                    lastRun = datetime.datetime.fromtimestamp(lastRun)

            now = datetime.datetime.utcnow()
            channels = [c for c in s.channels if c.name in svrOpts["textChannels"]]
            dumpDir = os.path.join(serverDir, "incoming")
            for channel in channels:
                try:
                    await dumpChannel(client,
                                channel, 
                                dumpDir, 
                                channel.name == "lewds", 
                                fromTime = lastRun, 
                                toTime = now)
                except Exception as e:
                    log_text(e)
                    raise
                        
            with open(timeFile, "w") as f:
                f.write("{0}".format(now.timestamp()))
            
        log_text ("Finished dumping all\n")
        await asyncio.sleep(180)
try:
    client.run(tok)
except Exception as e:
    log_text("something went wrong while running")
    log_text(e)
