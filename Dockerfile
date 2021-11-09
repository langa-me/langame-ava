FROM python:3.7-slim AS compile-image
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc && pip3 install virtualenv

RUN virtualenv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# git clone https://github.com/langa-me/ParlAI.git
COPY ./ParlAI ./ParlAI
RUN pip install transformers fairseq ./ParlAI

FROM python:3.7-slim AS build-image
COPY --from=compile-image /opt/venv /opt/venv

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY ./langame-ava/ava/*.py ./

ENTRYPOINT ["python", "run.py"]
CMD ["--config_path", "./config.yaml", "--port", "8080"]