# pull official base image
FROM python:3.10-slim-buster

# set working directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# RUN apt-get update \
#    # && apt-get -y install gcc postgresql vim\
#    && apt-get -y install vim\
#    && apt-get clean

# copy files and install python dependencies
COPY . .
RUN pip install poetry; poetry config virtualenvs.create false; poetry install --only main --no-interaction --no-ansi

ENTRYPOINT [ "./run_service.sh"]