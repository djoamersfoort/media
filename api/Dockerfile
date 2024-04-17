FROM python:3.11-slim

RUN apt -yy update && apt -yy install ffmpeg cmake build-essential && apt clean

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN useradd -m -U -d /app media
USER media
WORKDIR /app

COPY . /app
RUN chmod +x /app/start.sh

ENV PYTHONPATH=/
ENTRYPOINT ["/app/start.sh"]
