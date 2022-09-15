#syntax=docker/dockerfile:1

FROM python:3.8-slim-buster
WORKDIR /briar-python
RUN apt-get update -y
RUN apt-get install -y cmake build-essential libglib2.0-0 libsm6 libxrender1 libxext6
COPY lib/python/Briar/requirements.txt lib/python/Briar/requirements.txt
RUN pip3 install -r lib/python/Briar/requirements.txt
COPY lib/python lib/python
COPY weights weights
COPY media media
COPY setup.py setup.py
ENV BRIAR_DIR /briar-python
RUN python setup.py install
