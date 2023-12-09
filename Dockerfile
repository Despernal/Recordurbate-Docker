FROM python:alpine

WORKDIR /app

RUN apk add ffmpeg curl bash && \
    curl https://codeload.github.com/oliverjrose99/Recordurbate/zip/master --output master.zip && \
    unzip master.zip ; mv Recordurbate-master/recordurbate/* .;rm -r Recordurbate-master && \
    rm master.zip && \
    # curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl && \
    curl -L https://github.com/ytdl-org/youtube-dl/releases/download/2021.12.17/youtube-dl -o /usr/local/bin/youtube-dl && \
    chmod a+rx /usr/local/bin/youtube-dl && \
    pip install requests && \
    apk del curl

COPY run.sh /app/

RUN chmod +x run.sh

COPY config.json /app/configs/

COPY youtube-dl.config /app/configs/ 

CMD ["/app/run.sh" ]
