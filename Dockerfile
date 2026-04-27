FROM python:3.13-alpine3.22

WORKDIR /app

# N_m3u8DL-RE pinned by version + sha256. Using the musl-native build so we
# don't need gcompat. ffmpeg stays in for the muxing pipe (--live-pipe-mux).
# yt-dlp stays installed as a fallback for any non-CMAF / non-Chaturbate use.
ARG N_M3U8DL_RE_VERSION=v0.5.1-beta
ARG N_M3U8DL_RE_DATE=20251029
ARG N_M3U8DL_RE_SHA256=7105e26b76b099b41fcd490b9d09b3d43be971a880b6323fb988b688be00ab82
# Pin the upstream Recordurbate source to a specific commit so future builds
# can't drift if upstream changes. SHA 0479d71a is the last touch on master
# (2023-12-12) and matches what bot.py.patch was generated against. The
# codeload URL with /zip/<sha> always returns the tree at that commit.
ARG RECORDURBATE_SHA=0479d71a4e37b6efcd4a5eac1bbceb5b4592beb8

RUN apk add --no-cache ffmpeg bash patch && \
    apk add --no-cache --virtual .build curl && \
    curl -sL https://codeload.github.com/oliverjrose99/Recordurbate/zip/${RECORDURBATE_SHA} --output recordurbate.zip && \
    unzip recordurbate.zip && \
    mv Recordurbate-${RECORDURBATE_SHA}/recordurbate/* . && \
    rm -r Recordurbate-${RECORDURBATE_SHA} && \
    rm recordurbate.zip && \
    curl -sL https://github.com/ytdl-org/youtube-dl/releases/download/2021.12.17/youtube-dl -o /usr/local/bin/youtube-dl && \
    chmod a+rx /usr/local/bin/youtube-dl && \
    pip install --no-cache-dir requests yt-dlp && \
    curl -sL https://github.com/nilaoda/N_m3u8DL-RE/releases/download/${N_M3U8DL_RE_VERSION}/N_m3u8DL-RE_${N_M3U8DL_RE_VERSION}_linux-musl-x64_${N_M3U8DL_RE_DATE}.tar.gz -o /tmp/n.tgz && \
    echo "${N_M3U8DL_RE_SHA256}  /tmp/n.tgz" | sha256sum -c - && \
    tar xzf /tmp/n.tgz -C /usr/local/bin && \
    chmod +x /usr/local/bin/N_m3u8DL-RE && \
    rm -f /tmp/n.tgz && \
    apk del .build

COPY run.sh /app/

COPY bot.py.patch /app

RUN patch /app/bot.py  < /app/bot.py.patch

RUN chmod +x run.sh

COPY config.json /app/configs/

COPY youtube-dl.config /app/configs/

CMD ["/app/run.sh" ]
