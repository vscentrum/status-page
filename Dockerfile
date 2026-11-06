# Pin the Python and Debian base used for production rendering.
FROM python:3.14.7-slim-trixie

# install git
RUN apt update; apt install -y git

# copy requirements file
COPY ./requirements.txt /tmp/requirements.txt

# ensure that the .bashrc contains initialization for conda
RUN pip install -r /tmp/requirements.txt

# clean up
RUN rm /tmp/requirements.txt
