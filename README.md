# guevoncitabot

Discord music bot (multi-guild) with birthdays and Chilean holiday announcements.

## Commands

- `!setchannel #canal` — set the music channel for this guild (Manage Server).
- `!setholidays #canal` — set the holiday-announcement channel (Manage Server).
- `!birthday DD/MM` / `!birthday` / `!birthday borrar` — save / show / clear your birthday.
- `!nextbirthday`, `!nextholiday` — next upcoming birthday / holiday.
- Bare `pause`/`pausa`, `resume`, `skip`, `clear`, and YouTube/YouTube Music/Spotify/Tidal/Apple Music links in the music channel.

## YouTube authentication

YouTube requires a proof-of-origin token and often rejects datacenter IPs. The
`bgutil-provider` sidecar in `docker-compose.yml` mints those tokens, and
`YTSource.py` points yt-dlp at it via `YTDL_POT_PROVIDER_URL`.

Verify it is working:

```sh
docker compose up -d --build
docker compose exec discord-bot yt-dlp -v "https://youtu.be/<id>"
# expect: PO Token Providers: bgutil:http-1.3.2
# and:    Generating a gvs PO Token for web client via bgutil HTTP server
```

### Cookies (optional)

If the PO token alone is not enough (flagged IP, age-restricted or members-only
videos), export a Netscape-format `cookies.txt` from a **throwaway** Google
account (private window → log in → open `youtube.com/robots.txt` → export → close
the window), then place it next to this compose file:

```sh
touch cookies.txt          # create it first so Docker mounts a file, not a dir
chmod 644 cookies.txt
# ...put your exported cookies in cookies.txt...
docker compose up -d --build
```

`docker-compose.yml` mounts `./cookies.txt` **read-only** at `/cookies/cookies.txt`;
`docker-entrypoint.sh` copies it to the writable `/data/cookies.txt` at startup.
This is required because yt-dlp rewrites the cookie jar on exit (to persist
rotated session cookies) and fails with `PermissionError` on a read-only file.
`YTDL_COOKIEFILE` points at that writable copy and is only used if the file exists.

To refresh expired cookies, replace `./cookies.txt` and restart:

```sh
docker compose restart discord-bot
```

At startup the bot logs its yt-dlp config:

```
yt-dlp config: player_client=default,web_safari, pot_provider=http://bgutil-provider:4416, cookies=/data/cookies.txt (N cookies)
```

> Use a throwaway Google account. Sessions used by downloaders can be flagged,
> and the file is a live login token in plain text — never commit it.


### Tuning

- `YTDL_PLAYER_CLIENT` (default `default,web_safari`) — the working client list
  rotates; change it without rebuilding if extraction starts failing.
- `YTDL_POT_PROVIDER_URL` — set empty to disable the PO-token provider.
