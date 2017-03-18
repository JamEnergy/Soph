import discord
import soph
import importlib
import asyncio

client = discord.Client()
my_soph = soph.Soph()
tok = open("token.dat").read()


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.event
async def on_message(message):
    if message.content.startswith('!test'):
        counter = 0
        tmp = await client.send_message(message.channel, 'Calculating messages...')
        async for log in client.logs_from(message.channel, limit=100):
            if log.author == message.author:
                counter += 1

        await client.edit_message(tmp, 'You have {} messages.'.format(counter))
    elif message.content.startswith('!sleep'):
        await asyncio.sleep(5)
        await client.send_message(message.channel, 'Done sleeping')
    else:
        try:
            global my_soph
            if soph.reload(soph, "soph.py"):
                my_soph = soph.Soph(my_soph.corpus)

            my_soph.setClient(client)
            response = await my_soph.consume(message)
            if response:
                await client.send_message(message.channel, response)
        except Exception as e:
            print(e)


client.run(tok)
