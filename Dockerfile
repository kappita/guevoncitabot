FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus-dev \
    libffi-dev \
    libnacl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp needs a JavaScript runtime for YouTube extraction; Deno is
# enabled by default, so just having it on PATH is enough.
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

# Create a non-root user for security
RUN useradd -m -u 1000 botuser

WORKDIR /app

# Install Python dependencies first (layer caching)
# yt-dlp[default] pulls in the EJS challenge-solver scripts (yt-dlp-ejs).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source
COPY --chown=botuser:botuser . .
RUN chmod +x docker-entrypoint.sh

USER botuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py"]