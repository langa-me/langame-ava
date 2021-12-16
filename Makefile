REGISTRY ?= gcr.io/$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)/ava
VERSION ?= latest
OPENAI_KEY ?= $(shell cat .env | grep OPENAI_KEY | cut -d '=' -f 2)
OPENAI_ORG ?= $(shell cat .env | grep OPENAI_ORG | cut -d '=' -f 2)
HUGGINGFACE_TOKEN ?= $(shell cat .env | grep HUGGINGFACE_TOKEN | cut -d '=' -f 2)
HUGGINGFACE_KEY ?= $(shell cat .env | grep HUGGINGFACE_KEY | cut -d '=' -f 2)
SVC_DEV_PATH ?= "./svc.dev.json"
SVC_PROD_PATH ?= "./svc.prod.json"
GCLOUD_PROJECT:=$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)
gcloud_set_prod: ## Set the GCP project to prod
	gcloud config set project langame-86ac4

gcloud_set_dev: ## Set the GCP project to dev
	gcloud config set project langame-dev

run: ## [Local development] run the main entrypoint
	python3 $(shell pwd)/ava/main.py --service_account_key_path=svc.dev.json \
		--fix_grammar False \
		--profanity_thresold tolerant \
		--completion_type huggingface_api

# "don't forget to eval $(cat .env | sed 's/^/export /')"

docker_build: ## [Local development] build the docker image
	mkdir -p third_party/langame-worker/langame
	cp -r ../langame-worker/langame/ third_party/langame-worker/
	cp ../langame-worker/setup.py third_party/langame-worker/setup.py
	docker build -t ${REGISTRY}:${VERSION} . -f ./Dockerfile --build-arg HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
	rm -rf third_party

docker_run: docker_build ## [Local development] run the docker container
	docker run \
		-v $(shell pwd)/svc.dev.json:/etc/secrets/primary/svc.json \
		-e OPENAI_KEY=${OPENAI_KEY} \
		-e OPENAI_ORG=${OPENAI_ORG} \
		-e HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN} \
		-e HUGGINGFACE_KEY=${HUGGINGFACE_KEY} \
		${REGISTRY}:${VERSION} --fix_grammar False --profanity_thresold tolerant --completion_type openai_api


k8s_deploy: ## [Local development] deploy to Kubernetes.
# 	hack unless we can let k3d access gcr
	k3d image import ${REGISTRY}:${VERSION} -c basic
	@if [ "${GCLOUD_PROJECT}" = *"dev"* ]; then\
        helm install ava helm -f helm/values-dev.yaml -n ava-dev --create-namespace;\
    else\
		helm install ava helm -f helm/values-prod.yaml -n ava-prod --create-namespace;\
	fi

k8s_undeploy: ## [Local development] undeploy from Kubernetes.
	@if [ "${GCLOUD_PROJECT}" = *"dev"* ]; then\
        helm uninstall ava -n ava-dev;\
    else\
		helm uninstall ava -n ava-prod;\
	fi

protos: ## [Local development] Generate protos.
	python3 -m grpc_tools.protoc \
		--python_out=. \
		--include_imports \
		--include_source_info \
		proto/ava/v1/*.proto

install: ## [Local development] Upgrade pip, install requirements, install package.
	(\
		python3 -m virtualenv env; \
		. env/bin/activate; \
		python3 -m pip install -U pip; \
		python3 -m pip install -e .; \
		python3 -m pip install -r requirements-test.txt; \
	)

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
