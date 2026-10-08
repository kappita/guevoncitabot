import os
import json
import time
import asyncio
import logging
import discord
from dotenv import load_dotenv
from aiohttp import web
import YTLink as ytl
from YTSource import getSongSource, getPlaylistSource


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("guevoncita")

load_dotenv('.env')
TOKEN = os.getenv('DISCORD_TOKEN')
CONFIG_PATH = os.getenv('CONFIG_PATH', 'config.json')
intents = discord.Intents.all()
client = discord.Client(intents=intents)

START = time.time()
stats = {"commands": 0}
_status_started = False

# Seeds the previously hardcoded single-server setup so the current server
# keeps working after upgrading to multi-guild config.
LEGACY_GUILD = 881368444791054386
LEGACY_CHANNEL = 890351893224755220
LEGACY_CONSOLE = 890656775915835392

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

_config = {}
_guilds = {}


class GuildState:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = []
        self.lock = asyncio.Lock()
        self.console_message = None
        self.prefetching = False


def state_for(guild_id):
    state = _guilds.get(guild_id)
    if state is None:
        state = GuildState(guild_id)
        _guilds[guild_id] = state
    return state


def load_config():
    global _config
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            _config = {int(k): v for k, v in json.load(f).items()}
    else:
        _config = {LEGACY_GUILD: {"channel_id": LEGACY_CHANNEL, "console_message_id": LEGACY_CONSOLE}}


def save_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(_config, f, indent=2)


# JSON status endpoint consumed by the kappa-dashboard "discord" widget.
async def status(request):
    return web.json_response({
        "connected": client.is_ready() and not client.is_closed(),
        "latency_ms": round(client.latency * 1000),
        "guilds": len(client.guilds),
        "users": sum(g.member_count or 0 for g in client.guilds),
        "commands": stats["commands"],
        "queue_len": sum(len(s.queue) for s in _guilds.values()),
        "uptime_s": int(time.time() - START),
        "ts": time.time(),
    })


async def start_status_server():
    app = web.Application()
    app.router.add_get("/status", status)
    runner = web.AppRunner(app)
    await runner.setup()
    host = os.getenv("STATUS_HOST", "0.0.0.0")
    port = int(os.getenv("STATUS_PORT", "8099"))
    await web.TCPSite(runner, host, port).start()
    log.info("Status endpoint listening on http://%s:%s/status", host, port)


def check_playlist(queue):
    if not queue:
        return ('No hay nada en la cola de reproducción. \n'
                'Agrega canciones escribiendo links de YouTube en el chat.')
    if len(queue) > 10:
        lines = [f'{10 - i}.- ' + queue[9 - i]['title'] for i in range(10)]
        return 'La playlist es:\n y ' + str(len(queue) - 10) + ' canciones más \n' + '\n'.join(lines)
    lines = [f'{len(queue) - i}.- ' + queue[len(queue) - 1 - i]['title'] for i in range(len(queue))]
    return 'La playlist es: \n' + '\n'.join(lines)


async def ensure_console(guild, state):
    if state.console_message is not None:
        return state.console_message
    cfg = _config.get(guild.id)
    if not cfg:
        return None
    channel = guild.get_channel(cfg['channel_id'])
    if channel is None:
        return None
    msg_id = cfg.get('console_message_id')
    if msg_id:
        try:
            state.console_message = await channel.fetch_message(msg_id)
            return state.console_message
        except discord.NotFound:
            pass
    state.console_message = await channel.send('Cola de reproducción lista.')
    cfg['console_message_id'] = state.console_message.id
    save_config()
    return state.console_message


async def edit_console(state, **kwargs):
    msg = state.console_message
    if msg is None:
        return
    try:
        await msg.edit(**kwargs)
    except discord.NotFound:
        state.console_message = None


# Runs in the voice thread when a track ends, so it hops back onto the event loop.
def after_play(guild):
    fut = asyncio.run_coroutine_threadsafe(play_next(guild), client.loop)
    try:
        fut.result()
    except Exception:
        log.exception("play_next failed for guild %s", guild.id)


async def prefetch_next(state):
    async with state.lock:
        if state.prefetching or not state.queue or state.queue[0]['extracted']:
            return
        state.prefetching = True
        search = state.queue[0]['search']
    source = await asyncio.to_thread(getSongSource, search)
    async with state.lock:
        state.prefetching = False
        if state.queue and state.queue[0].get('search') == search and not state.queue[0]['extracted']:
            state.queue[0] = source


async def play_next(guild):
    state = state_for(guild.id)
    async with state.lock:
        vc = guild.voice_client
        if vc is None or not vc.is_connected():
            return
        console = await ensure_console(guild, state)

        if not state.queue:
            if console is not None:
                embed = discord.Embed(title='No estoy tocando nada en este momento. \n'
                                            'Coloca alguna canción escribiendo su link de YouTube en el chat')
                embed.set_image(url='https://i.ytimg.com/vi/86O_FZ1Ph4I/maxresdefault.jpg')
                await edit_console(state, content='', embed=embed)
            return

        source = state.queue.pop(0)
        if not source['extracted']:
            source = await asyncio.to_thread(getSongSource, source['search'])

        audio = await discord.FFmpegOpusAudio.from_probe(source['source'], method='fallback', **FFMPEG_OPTIONS)
        vc.play(audio, after=lambda e=None: after_play(guild))

        if console is not None:
            embed = discord.Embed(title='Ahora estás escuchando: ' + source['title'],
                                  url='https://www.youtube.com/watch?v=' + source['id'])
            embed.set_image(url=source['thumbnail'])
            await edit_console(state, content=check_playlist(state.queue), embed=embed)

        if state.queue and not state.queue[0]['extracted']:
            asyncio.create_task(prefetch_next(state))


async def sources_from_url(url):
    media = url['mediaSource']
    sources = []
    if media == 'youtube':
        if url['type'] in ('short', 'song'):
            sources.append(await asyncio.to_thread(getSongSource, url['entries'][0]['url']))
        elif url['type'] == 'playlist':
            sources.extend(await asyncio.to_thread(getPlaylistSource, url['entries'][0]['url']))
        elif url['type'] == 'search':
            sources.append(await asyncio.to_thread(getSongSource, url['entries'][0]['search']))
    elif media in ('spotify', 'tidal'):
        if url['type'] == 'song':
            source = await asyncio.to_thread(getSongSource, url['entries'][0]['search'])
            source['title'] = url['entries'][0]['title']
            sources.append(source)
        elif url['type'] == 'playlist':
            for song in url['entries']:
                sources.append({'extracted': False, 'title': song['title'], 'search': song['search']})
    return sources


async def handle_setchannel(message):
    if message.guild is None:
        return
    if not message.author.guild_permissions.manage_guild:
        err = await message.channel.send('Necesitas el permiso "Gestionar servidor" para configurar el canal.')
        await err.delete(delay=5)
        return
    if not message.channel_mentions:
        err = await message.channel.send('Uso: !setchannel #canal')
        await err.delete(delay=5)
        return

    channel = message.channel_mentions[0]
    _config[message.guild.id] = {'channel_id': channel.id}
    save_config()
    state_for(message.guild.id).console_message = None

    try:
        await message.delete()
    except discord.HTTPException:
        pass

    await ensure_console(message.guild, state_for(message.guild.id))
    await message.channel.send(f'Canal de música configurado: {channel.mention}', delete_after=5)


@client.event
async def on_ready():
    global _status_started
    if not _status_started:
        _status_started = True
        asyncio.create_task(start_status_server())

    await client.change_presence(activity=discord.Game('Gwagwa'))
    log.info('Güevoncita se conectó como %s', client.user)

    # Tidy each configured music channel, preserving the console message.
    for guild_id, cfg in list(_config.items()):
        guild = client.get_guild(guild_id)
        if guild is None:
            continue
        channel = guild.get_channel(cfg['channel_id'])
        if channel is None:
            continue
        keep = {cfg.get('console_message_id')}
        try:
            async for msg in channel.history(limit=200):
                if msg.id not in keep:
                    await msg.delete()
        except discord.HTTPException:
            pass


@client.event
async def on_message(message):
    if message.author == client.user or message.author.bot:
        return

    content = message.content.strip()
    if content.startswith('!setchannel'):
        await handle_setchannel(message)
        return

    cfg = _config.get(message.guild.id) if message.guild else None
    if not cfg or message.channel.id != cfg['channel_id']:
        return

    await message.delete()
    guild = message.guild
    state = state_for(guild.id)
    await ensure_console(guild, state)

    vc = guild.voice_client
    if vc is None:
        author_voice = getattr(message.author.voice, 'channel', None)
        if author_voice is None:
            err = await message.channel.send('Debes estar conectado a un canal')
            await err.delete(delay=3)
            return
        vc = await author_voice.connect()

    low = content.lower()
    if low in ('pause', 'pausa'):
        vc.pause()
        stats["commands"] += 1
        return
    if low == 'resume':
        vc.resume()
        stats["commands"] += 1
        return
    if low == 'skip':
        vc.stop()
        stats["commands"] += 1
        return
    if low == 'clear':
        async with state.lock:
            state.queue.clear()
        stats["commands"] += 1
        await edit_console(state, content='No hay nada en la cola de reproducción. \n'
                                          'Agrega canciones escribiendo links de YouTube en el chat.', embed=None)
        return

    try:
        url = await asyncio.to_thread(ytl.YTid, content)
        sources = await sources_from_url(url)
    except Exception:
        log.exception("failed to resolve %r", content)
        err = await message.channel.send('No pude procesar ese link, pillín ;)')
        await err.delete(delay=3)
        return

    async with state.lock:
        state.queue.extend(sources)
        should_start = not vc.is_playing() and not vc.is_paused()
        if not should_start:
            await edit_console(state, content=check_playlist(state.queue))

    stats["commands"] += 1

    if should_start:
        await play_next(guild)


load_config()
client.run(TOKEN)
