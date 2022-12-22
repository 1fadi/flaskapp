FROM python:3.11-alpine

ENV FLASK_APP main.py
ENV FLASK_CONFIG docker

RUN adduser -D flaskuser
USER flaskuser

WORKDIR /home/flaskuser

COPY requirements requirements
RUN python -m venv env
RUN env/bin/pip install -r requirements/docker.txt

COPY app app
COPY migrations migrations
COPY main.py config.py boot.sh ./

# runtime configuration
EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
