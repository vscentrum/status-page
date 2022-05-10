# base image provided bij Continuum with miniconda3 preinstalled
FROM python:3.10.4-slim-buster

# install git
RUN apt update; apt install -y git

# copy requirements file
COPY ./requirements.txt /tmp/requirements.txt

# ensure that the .bashrc contains initialization for conda
RUN pip install -r /tmp/requirements.txt

# clean up
RUN rm /tmp/requirements.txt
