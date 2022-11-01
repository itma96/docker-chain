FROM python:2.7-alpine

RUN apk add build-base

WORKDIR /worker

ADD requirements.txt /worker/requirements.txt
RUN pip install --no-cache-dir -r /worker/requirements.txt

ADD worker.py /worker/worker.py
ADD blockchain.py /worker/blockchain.py
ADD static /worker/static
ADD templates /worker/templates

EXPOSE 5000
