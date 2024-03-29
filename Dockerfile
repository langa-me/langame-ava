FROM nvidia/cuda:11.5.0-base-ubuntu20.04
USER root
RUN apt-get update
RUN apt-get install -y --no-install-recommends python3.8 python3-pip build-essential gcc && pip3 install virtualenv

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
COPY .pypirc /root/.pypirc
COPY pip.conf /root/.config/pip/pip.conf
RUN pip install -e .

# FROM python:3.8-slim AS build-image
# COPY --from=compile-image /opt/venv /opt/venv

# Make sure we use the virtualenv:
# ENV PATH="/opt/venv/bin:$PATH"
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED 0

# Copy local code to the container image.
# ENV APP_HOME /app
# WORKDIR $APP_HOME
# COPY --from=compile-image /ava.egg-info ava.egg-info
USER ${UID}:${GID}

# Writing models in the container
# RUN python -c "import os; from transformers import GPT2LMHeadModel, AutoTokenizer; GPT2LMHeadModel.from_pretrained('Langame/distilgpt2-starter', use_auth_token=os.environ.get('HUGGINGFACE_TOKEN')); AutoTokenizer.from_pretrained('Langame/distilgpt2-starter', use_auth_token=os.environ.get('HUGGINGFACE_TOKEN'))"
# RUN python -c "import os; from transformers import T5ForConditionalGeneration, T5Tokenizer; T5Tokenizer.from_pretrained('flexudy/t5-small-wav2vec2-grammar-fixer'); T5ForConditionalGeneration.from_pretrained('flexudy/t5-small-wav2vec2-grammar-fixer')"
ENTRYPOINT ["/opt/venv/bin/python", "./ava/main.py"]
CMD ["--profanity_threshold", "tolerant", "--completion_type", "huggingface_api", "--tweet_on_generate", "False"]