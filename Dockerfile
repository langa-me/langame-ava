FROM python:3.8-slim AS compile-image
USER root
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc && pip3 install virtualenv

RUN virtualenv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

ARG HUGGINGFACE_TOKEN=foo
ARG USER=docker
ARG UID=1000
ARG GID=1000
# default password for user
ARG PW=docker
# Option1: Using unencrypted password/ specifying password
RUN useradd -m ${USER} --uid=${UID} && echo "${USER}:${PW}" | chpasswd
RUN mkdir -p /home/${USER}
RUN chown ${USER} /home/${USER}
# Setup default user, when enter docker container
WORKDIR /home/${USER}

COPY ava ./ava/
COPY ./setup.py ./setup.py
COPY ./third_party/langame-worker/langame/ ../langame-worker/langame/
COPY ./third_party/langame-worker/setup.py ../langame-worker/setup.py
RUN pip install -e .

# FROM python:3.8-slim AS build-image
# COPY --from=compile-image /opt/venv /opt/venv

# Make sure we use the virtualenv:
# ENV PATH="/opt/venv/bin:$PATH"
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
# ENV APP_HOME /app
# WORKDIR $APP_HOME
# COPY --from=compile-image /ava.egg-info ava.egg-info
USER ${UID}:${GID}

# RUN python -c "import os; from transformers import pipeline, set_seed, TextGenerationPipeline; pipeline('text-generation', model='Langame/gpt2-starter', tokenizer='gpt2', use_auth_token=os.environ.get('HUGGINGFACE_TOKEN'))"
ENTRYPOINT ["/opt/venv/bin/python", "./ava/main.py"]
CMD ["--fix_grammar", "False", "--profanity_thresold", "tolerant", "--completion_type", "huggingface_api"]