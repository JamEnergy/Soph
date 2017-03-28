import discord
import soph
import importlib
import asyncio
import traceback

client = discord.Client()
my_soph = soph.Soph()
my_soph.setClient(client)
tok = open("token.dat").read()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    #await client.change_presence(game = discord.Game(name="with your chat data"))
    print('------')

@client.event
async def on_message(message):
    try:
        global my_soph
        if soph.reload(soph, "soph.py"):
            my_soph = soph.Soph(my_soph.corpus)
            my_soph.setClient(client)
        response = await my_soph.consume(message)
        if response:
            await client.send_message(message.channel, response[0:1000])
    except Exception as e:
        print (e)
        print (traceback.format_exc())

client.run(tok)

