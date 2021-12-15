REGISTRY ?= gcr.io/$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)/conversation-starter
VERSION ?= latest
OPENAI_KEY ?= $(shell cat .env | grep OPENAI_KEY | cut -d '=' -f 2)
OPENAI_ORG ?= $(shell cat .env | grep OPENAI_ORG | cut -d '=' -f 2)
HUGGINGFACE_TOKEN ?= $(shell cat .env | grep HUGGINGFACE_TOKEN | cut -d '=' -f 2)
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

docker_build: ## [Local development] build the docker image
	mkdir -p third_party
	cp -r ../langame-worker/{langame,setup.py} third_party/
	docker build -t ${REGISTRY}:${VERSION} . -f ./Dockerfile --build-arg HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
	rm -rf third_party

docker_run: docker_build ## [Local development] run the docker container
	# "don't forget to eval $(cat .env | sed 's/^/export /')"
	docker run \
		-v $(shell pwd)/svc.dev.json:/etc/secrets/primary/svc.json \
		-e OPENAI_KEY=${OPENAI_KEY} \
		-e OPENAI_ORG=${OPENAI_ORG} \
		-e HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN} \
		${REGISTRY}:${VERSION} --fix_grammar False --profanity_thresold tolerant --completion_type huggingface_api

k8s_create_svc: ## [Local development] create service account in Kubernetes.
	# gcloud iam service-accounts create pull-image-gcr \
	# 	--description="pull image gcr from k8s" \
	# 	--display-name="pull-image-gcr" \
	# 	--project=${GCLOUD_PROJECT}
	# gcloud iam service-accounts add-iam-policy-binding $(shell gcloud iam service-accounts list --filter="pull-image-gcr" --format 'value(email)') \
	# 	--member user:louis.beaumont@gmail.com \
	# 	--project=${GCLOUD_PROJECT} \
	# 	--role roles/viewer
	# Download as key
	# gcloud iam service-accounts keys create ./pull-image-gcr.json \
	# 	--iam-account=$(shell gcloud iam service-accounts list --filter="pull-image-gcr" --format 'value(email)') \
	# 	--project=${GCLOUD_PROJECT}
	kubectl create secret docker-registry langame-dev-registry \
		--docker-server=gcr.io \
		--docker-username=_json_key \
		--docker-email=louis.beaumont@gmail.com \
		--docker-password='$(shell cat pull-image-gcr.json)' \
		-n ava
	# kubectl patch serviceaccount default \
	# 	-p '{"imagePullSecrets": [{"name": "langame-dev-registry"}]}'


k8s_deploy: ## [Local development] deploy to Kubernetes.
# 	hack unless we can let k3d access gcr
	# k3d image import ${REGISTRY}:${VERSION} -c basic
	helm install ava helm -f helm/values-dev.yaml -n ava --create-namespace

k8s_undeploy: ## [Local development] undeploy from Kubernetes.
	helm uninstall ava -n ava

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
