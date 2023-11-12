import os
import asyncio
import discord
from discord import FFmpegPCMAudio
from discord.player import FFmpegOpusAudio
from dotenv import load_dotenv
import YTLink as ytl
from YTSource import getSongSource, getPlaylistSource


load_dotenv('.env')
TOKEN = os.environ['DISCORD_TOKEN']
intents = discord.Intents.all()
meses = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
client = discord.Client(intents=intents)
idserver = 881368444791054386 
queue = []

## The function to check the state of the playlist and return a message
def check_playlist(queue):

    ## If the queue has more than 10 entries
    if len(queue) > 10:

        playlistmessage = 'La playlist es:\n y ' + str(len(queue) - 10) + ' canciones más \n'
        for songplace in range(10):
            playlistmessage += str(10-songplace) + '.- ' + queue[9 - songplace]['title'] + '\n'

    ## If the queue has 10 or less entries
    elif len(queue) <= 10 and len(queue) != 0:

        playlistmessage = 'La playlist es: \n'
        for songplace in range(len(queue)):
            playlistmessage += str(len(queue)-songplace) + '.- ' + queue[len(queue) - 1 - songplace]['title'] + '\n'       

    ## If the queue doesn't have any entry
    else:

        playlistmessage = 'No hay nada en la cola de reproducción. \nAgrega canciones escribiendo links de YouTube en el chat.'       
    ## Returns the message created with the queue info 
    return playlistmessage


# Checks the music queue when the current song stops or is stopped,
# in order to play the next one in the queue
def check_queue(voiceclient, playlistchannel):
    global queue
    if queue != []:
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        source = queue.pop(0)

        if source['extracted'] == False:
            source = getSongSource(source['search'])

        nextaudio = discord.FFmpegOpusAudio.from_probe(source['source'], method='fallback', **FFMPEG_OPTIONS)
        fut = asyncio.run_coroutine_threadsafe(nextaudio, client.loop)
        try:
            nextaudio = fut.result()
            voiceclient.play(nextaudio, after=lambda x=None: check_queue(voiceclient, playlistchannel))
        except:
            pass

        embedmessage = 'Ahora estás escuchando: ' + source['title']
        nowplaying = discord.Embed(title=embedmessage, url= 'https://www.youtube.com/watch?v=' + source['id'])
        nowplaying.set_image(url=source['thumbnail'])
        coro = playlistchannel.edit(content=check_playlist(queue), embed=nowplaying)  
        fut = asyncio.run_coroutine_threadsafe(coro, client.loop)    
        try:
             fut.result()
        except:
            pass

        if queue != []:
            if queue[0]['extracted'] == False:
                getSongSource(queue[0]['search'])
    else:
        embedmessage = 'No estoy tocando nada en este momento. \nColoca alguna canción escribiendo su link de YouTube en el chat'
        nowplaying = discord.Embed(title=embedmessage)
        nowplaying.set_image(url='https://i.ytimg.com/vi/86O_FZ1Ph4I/maxresdefault.jpg')
        coro = playlistchannel.edit(content='', embed=nowplaying)  
        fut = asyncio.run_coroutine_threadsafe(coro, client.loop)    
        try:
             fut.result()
        except:
            pass


## Sets bot's configuration 
@client.event
async def on_ready():
    testguild = client.get_guild(idserver)
    game = discord.Game('Gwagwa')
    await client.change_presence(activity=game)
    print('Güevoncita se conectó')

    music_channel = testguild.get_channel(890351893224755220)

    async for message in music_channel.history(limit=200):
        if message.id not in [890656762594725908, 890656775915835392]:
            await message.delete()

@client.event
async def on_message(message):
    global queue

    ## Ignores the message if the author is the bot
    if message.author == client.user:
        return
    ## If the message comes from the music channel
    if message.channel.id == 890351893224755220: 
        await message.delete()
        consolemessage = await message.channel.fetch_message(890656775915835392) 
        try:
            vc = client.voice_clients[0]
        except:
            try:
                vc = await message.author.voice.channel.connect()

            except:
                errormessage = await message.channel.send('Debes estar conectado a un canal')
                await errormessage.delete(delay=3)
                return

        ##Simple commands to workaround with the music player

        if message.content.lower() == 'pause' or message.content.lower() == 'pausa':
            vc.pause()

        elif message.content == 'resume':
            vc.resume()

        elif message.content == 'skip':
            vc.stop()

        elif message.content == 'clear':
            queue = []
            await consolemessage.edit(content='No hay nada en la cola de reproducción. \nAgrega canciones escribiendo links de YouTube en el chat.')


        else:

            url = ytl.YTid(message.content)
            if url['mediaSource'] == 'youtube':
                if url['type'] == 'short':
                    source = getSongSource(url['entries'][0]['url'])
                    queue.append(source)

                if url['type'] == 'song':
                    source = getSongSource(url['entries'][0]['url'])
                    queue.append(source)

                if url['type'] == 'playlist':
                    sources = getPlaylistSource(url['entries'][0]['url'])
                    for source in sources:
                        queue.append(source)

                if url['type'] == 'search':
                    source = getSongSource(url['entries'][0]['search'])
                    queue.append(source)

            elif url['mediaSource'] == 'spotify':
                if url['type'] == 'song':
                    source = getSongSource(url['entries'][0]['search'])
                    source['title'] = url['entries'][0]['title']
                    queue.append(source)

                if url['type'] == 'playlist':
                    for song in url['entries']:
                        queue.append({'extracted': False, 'title': song['title'], 'search': song['search']})

            if url == 'Not YTL':
                errormessage = await message.channel.send('Ese no es un link de Youtube, pillín ;)')
                await errormessage.delete(delay=3)
                return



            ## Declares the configuration for ytdl and opusfromprobe
            FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
            

            ## If the bot isn't playing any music
            if vc.is_playing() == False:
                source = queue.pop(0)
                if source['extracted'] == False:
                    source = getSongSource(source['search'])

                embedmessage = 'Ahora estás escuchando: ' + source['title']
                newurl = 'https://www.youtube.com/watch?v=' + source['id']
                nowplaying = discord.Embed(title=embedmessage, url=newurl)
                nowplaying.set_image(url=source['thumbnail'])
                await consolemessage.edit(content=check_playlist(queue), embed=nowplaying)  


                audio = await discord.FFmpegOpusAudio.from_probe(source['source'], method='fallback', **FFMPEG_OPTIONS)
                vc.play(audio, after=lambda x=None: check_queue(vc, consolemessage))     
                
                if queue != []:
                    if queue[0]['extracted'] == False:
                        queue[0] = getSongSource(queue[0]['search'])

            elif vc.is_playing() == True:       

                await consolemessage.edit(content=check_playlist(queue))  

                if queue[0]['extracted'] == False:
                        queue[0] = getSongSource(queue[0]['search'])


client.run(TOKEN)

