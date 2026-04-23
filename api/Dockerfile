FROM python:3.12-slim

RUN apt-get -y update && apt-get -y install ffmpeg && apt-get -y clean

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN useradd -m -U -d /app media
WORKDIR /app

COPY --chown=media:media . /app
RUN chmod +x /app/start.sh

USER media

ENV PYTHONPATH=/
ENTRYPOINT ["/app/start.sh"]
