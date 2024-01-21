FROM python:3.11-slim

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN useradd -m -U -d /app media
USER media
WORKDIR /app

COPY app /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
