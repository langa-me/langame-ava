FROM python:3.7-slim AS compile-image
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc && pip3 install virtualenv

RUN virtualenv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# because https://github.com/huggingface/tokenizers/tree/master/bindings/python
# RUN apt-get update && apt-get install -y git curl &&\
#     curl https://sh.rustup.rs -sSf | sh -s -- -y &&\
#     export PATH="$HOME/.cargo/bin:$PATH" &&\
#     git clone https://github.com/huggingface/tokenizers &&\
#     cd tokenizers/bindings/python &&\
#     pip install setuptools_rust &&\
#     python setup.py install

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.7-slim AS build-image
COPY --from=compile-image /opt/venv /opt/venv

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"
# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
#CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 run:app
ENTRYPOINT ["python", "run.py", "--config_path", "tasks/chatbot/config.yml", "--port", "8080"]