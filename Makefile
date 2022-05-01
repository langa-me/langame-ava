REGISTRY ?= 5306t2h8.gra7.container-registry.ovh.net/$(shell cat .env | grep OVH_PROJECT_ID | cut -d '=' -f 2)/ava
# take version in setup.py, only what's between the quotes """
VERSION ?= $(shell cat setup.py | grep version | cut -d '"' -f 2)
OPENAI_KEY ?= $(shell cat .env | grep OPENAI_KEY | cut -d '=' -f 2)
OPENAI_ORG ?= $(shell cat .env | grep OPENAI_ORG | cut -d '=' -f 2)
HUGGINGFACE_TOKEN ?= $(shell cat .env | grep HUGGINGFACE_TOKEN | cut -d '=' -f 2)
HUGGINGFACE_KEY ?= $(shell cat .env | grep HUGGINGFACE_KEY | cut -d '=' -f 2)
SVC_DEV_PATH ?= "./svc.dev.json"
SVC_PROD_PATH ?= "./svc.prod.json"
GCLOUD_PROJECT:=$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)
K8S_NAMESPACE=$(shell cat .env | grep K8S_NAMESPACE | cut -d '=' -f 2)
HELM_VALUES=$(shell cat .env | grep HELM_VALUES | cut -d '=' -f 2)

prod: ## Set the GCP project to prod
	@gcloud config set project langame-86ac4 2>/dev/null
	@sed -i 's/OVH_PROJECT_ID=.*/OVH_PROJECT_ID="prod"/' .env
	@sed -i 's/K8S_NAMESPACE=.*/K8S_NAMESPACE="ava-prod"/' .env
	@sed -i 's/HELM_VALUES=.*/HELM_VALUES="helm\/values-prod.yaml"/' .env
	@echo "Configured prod GCP project, OVHCloud project and k8s"

dev: ## Set the GCP project to dev
	@gcloud config set project langame-dev 2>/dev/null
	@sed -i 's/OVH_PROJECT_ID=.*/OVH_PROJECT_ID="dev"/' .env
	@sed -i 's/K8S_NAMESPACE=.*/K8S_NAMESPACE="ava-dev"/' .env
	@sed -i 's/HELM_VALUES=.*/HELM_VALUES="helm\/values-dev.yaml"/' .env
	@echo "Configured dev GCP project, OVHCloud project and k8s"

docker/build: ## [Local development] build the docker image
	mkdir -p third_party/langame-worker/langame
	cp -r ../langame-worker/langame/ third_party/langame-worker/
	cp ../langame-worker/setup.py third_party/langame-worker/setup.py
	docker buildx build -t ${REGISTRY}:${VERSION} . -f ./Dockerfile --build-arg HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
	rm -rf third_party

docker/run: docker/build ## [Local development] run the docker container
	docker run \
		-v $(shell pwd)/svc.dev.json:/etc/secrets/primary/svc.json \
		-e OPENAI_KEY=${OPENAI_KEY} \
		-e OPENAI_ORG=${OPENAI_ORG} \
		-e HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN} \
		-e HUGGINGFACE_KEY=${HUGGINGFACE_KEY} \
		${REGISTRY}:${VERSION} \
		--profanity_threshold tolerant \
		--completion_type local \
		--tweet_on_generate False \
		--use_gpu False

docker/push: docker/build ## [Local development] push the docker image to GCR
	docker push ${REGISTRY}:${VERSION}
	docker push ${REGISTRY}:latest

k8s/deploy: ## [Local development] deploy to Kubernetes.
	helm install ava helm -f ${HELM_VALUES} -n ${K8S_NAMESPACE} --create-namespace
k8s/upgrade: ## [Local development] upgrade with new config.
	helm upgrade ava helm -f ${HELM_VALUES} -n ${K8S_NAMESPACE}
k8s/undeploy: ## [Local development] undeploy from Kubernetes.
	helm uninstall ava -n ${K8S_NAMESPACE}

release:
	@echo "Releasing version ${VERSION}"; \
	git add .; \
	read -p "Commit content:" COMMIT; \
	echo "Committing '${VERSION}: $$COMMIT'"; \
	git commit -m "${VERSION}: $$COMMIT"; \
	git push origin main; \
	git tag v${VERSION}; \
	git push origin v${VERSION}
	echo "Done, check https://github.com/langa-me/ava/actions"

# baremetal

run: ## [Local development] run the main entrypoint
	python3 $(shell pwd)/ava/main.py --service_account_key_path=svc.prod.json \
		--shard 0 \
		--only_sample_confirmed_conversation_starters True


clean:
	rm -rf env .pytest_cache *.egg-info **/*__pycache__ embeddings/ indexes index_infos.json

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
