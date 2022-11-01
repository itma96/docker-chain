FROM python:2.7-alpine

RUN apk add build-base

WORKDIR /client

ADD requirements.txt /client/requirements.txt 
RUN pip install --no-cache-dir -r /client/requirements.txt

ADD client.py /client/client.py
ADD transaction.py /client/transaction.py
ADD static /client/static
ADD templates /client/templates

EXPOSE 8080

