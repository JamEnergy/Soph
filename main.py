
import discord
import reloader
import sophLogger
import soph
import importlib
import asyncio
import traceback

client = discord.Client()
my_soph = soph.Soph(client=client)
tok = open("token.dat").read()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)


    #await client.change_presence(game = discord.Game(name="with your chat data"))
    print('------')
    global my_soph  # type:soph.Soph
    my_soph.onReady()
    listeners = my_soph.options["masters"] or [soph.Soph.master_id]
    for m,v in listeners.items():
        master_info = await client.get_user_info(m)
        await client.send_message(master_info, v or my_soph.greeting)

@client.event
async def on_error(event, *args, **kwargs):
    print(args)
    print(kwargs)
    print("Error?")

@client.event
async def on_message(message):
    try:
        global my_soph
        if reloader.reload(soph, "soph.py"):
            my_soph = soph.Soph(my_soph.corpus, client = client)
        response = await my_soph.consume(message)
        if response:
            await client.send_message(message.channel, response[0:1000])
    except Exception as e:
        print (e)
        print (traceback.format_exc())

try:
    client.run(tok)
except:
    print ("Exception")

