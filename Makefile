REGISTRY ?= gcr.io/$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)/conversation-starter
VERSION ?= latest
GATEWAY_FLAGS := -I ./proto -I include/googleapis -I include/grpc-gateway
OPENAI_KEY ?= foo
OPENAI_ORG ?= bar
HUGGINGFACE_TOKEN ?= baz
SVC_DEV_PATH ?= "./svc.dev.json"
SVC_PROD_PATH ?= "./svc.prod.json"
GCLOUD_PROJECT:=$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)
GCP_RUN_SVC:=$(shell gcloud iam service-accounts list --filter="Default compute service account" --format 'value(email)' 2>/dev/null)

gcloud_set_prod: ## Set the GCP project to prod
	gcloud config set project langame-86ac4

gcloud_set_dev: ## Set the GCP project to dev
	gcloud config set project langame-dev

docker_build: ## [Local development] build the docker image
	docker build -t ${REGISTRY}:${VERSION} . -f ./Dockerfile --build-arg HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}

docker_run: ## [Local development] run the docker container
	# "don't forget to eval $(cat .env | sed 's/^/export /')"
	docker run -p 8081:8080 \
		-v $(shell pwd)/svc.dev.json:/etc/secrets/primary/svc.json \
		-e OPENAI_KEY=${OPENAI_KEY} \
		-e OPENAI_ORG=${OPENAI_ORG} \
		-e HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN} \
		${REGISTRY}:${VERSION} --fix_grammar False --no_openai True

deploy_run: docker_build ## [Local development] deploy to GCP.
	echo "Asssuming using secret version 1"
	docker push ${REGISTRY}:${VERSION}
	gcloud run deploy conversation-starter \
		--project ${GCLOUD_PROJECT} \
		--image ${REGISTRY}:${VERSION} \
		--region us-central1 \
		--set-secrets "/etc/secrets/primary/svc.json=service_account_dev:1" \
		--set-secrets "OPENAI_KEY=openai_key:1" \
		--set-secrets "OPENAI_ORG=openai_org:1" \
		--set-secrets "HUGGINGFACE_TOKEN=huggingface_token:1" \
		--allow-unauthenticated \
		--memory=4Gi \
		--cpu=2 \
		--use-http2 \
		--max-instances=5
	gcloud run services update-traffic --to-revisions=LATEST=100 conversation-starter \
		--region us-central1 \
		--project ${GCLOUD_PROJECT}

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
	helm install ava helm -f helm/values-dev.yaml -n ava --create-namespace

k8s_undeploy: ## [Local development] undeploy from Kubernetes.
	helm uninstall ava -n ava

redoc: ## [Local development] redoc.
	docker run -p 8080:80 \
		-v $(shell pwd)/openapiv2/ava/v1:/usr/share/nginx/html/openapiv2/ \
		-e SPEC_URL=openapiv2/api.swagger.json \
		redocly/redoc

swagger: ## [Local development] Run a swagger.
	docker run -p 8080:8080 \
		-e SWAGGER_JSON=/openapiv2/ava/v1/api.swagger.json \
		-v $(shell pwd)/openapiv2/:/openapiv2 \
		swaggerapi/swagger-ui

lint: ## [Local development] Lint.
	openapi lint openapiv2/ava/v1/api.swagger.json

protos: ## [Local development] Generate protos, openapi, grpc-gateway proxy.
	mkdir -p openapiv2/
	# TODO https://cloud.google.com/api-gateway/docs/get-started-cloud-run-grpc
	protoc $(GATEWAY_FLAGS) \
		--openapiv2_out ./openapiv2 --openapiv2_opt logtostderr=true \
		--go_out=. \
		--go-grpc_out=. \
		--grpc-gateway_out=logtostderr=true:. \
		proto/ava/v1/*.proto
	python3 -m grpc_tools.protoc $(GATEWAY_FLAGS) \
		--python_out=. \
		--descriptor_set_out=ava/v1/api_descriptor.pb \
		--grpc_python_out=. \
		--include_imports \
		--include_source_info \
		proto/ava/v1/*.proto

deps: ## [Local development] Install dependencies.
	rm -rf include/googleapis/google
	mkdir -p include/googleapis/google/api include/googleapis/google/rpc
	wget https://raw.githubusercontent.com/googleapis/googleapis/master/google/api/http.proto -O include/googleapis/google/api/http.proto > /dev/null
	wget https://raw.githubusercontent.com/googleapis/googleapis/master/google/api/annotations.proto -O include/googleapis/google/api/annotations.proto > /dev/null
	wget https://raw.githubusercontent.com/googleapis/googleapis/master/google/rpc/code.proto -O include/googleapis/google/rpc/code.proto > /dev/null
	wget https://raw.githubusercontent.com/googleapis/googleapis/master/google/rpc/error_details.proto -O include/googleapis/google/rpc/error_details.proto > /dev/null
	wget https://raw.githubusercontent.com/googleapis/googleapis/master/google/rpc/status.proto -O include/googleapis/google/rpc/status.proto > /dev/null
	rm -rf include/grpc-gateway/protoc-gen-openapiv2
	mkdir -p include/grpc-gateway/protoc-gen-openapiv2/options
	wget https://raw.githubusercontent.com/grpc-ecosystem/grpc-gateway/master/protoc-gen-openapiv2/options/annotations.proto -O include/grpc-gateway/protoc-gen-openapiv2/options/annotations.proto > /dev/null
	wget https://raw.githubusercontent.com/grpc-ecosystem/grpc-gateway/master/protoc-gen-openapiv2/options/openapiv2.proto -O include/grpc-gateway/protoc-gen-openapiv2/options/openapiv2.proto > /dev/null
	# npm i -g @redocly/openapi-cli@latest
	go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest
	go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@latest
	go install github.com/grpc-ecosystem/grpc-gateway/protoc-gen-swagger@latest
	go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest


install: ## [Local development] Upgrade pip, install requirements, install package.
	(\
		python3 -m virtualenv env; \
		. env/bin/activate; \
		python3 -m pip install -U pip; \
		python3 -m pip install -e .; \
		python3 -m pip install -r requirements-test.txt; \
	)

create_secret: ##[Local development] create secret in GCP.
	
	# printf ${OPENAI_KEY} | gcloud secrets create openai_key --project ${GCLOUD_PROJECT} --data-file=-
	# gcloud beta secrets add-iam-policy-binding openai_key --project ${GCLOUD_PROJECT} --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor

	# printf ${OPENAI_ORG} | gcloud secrets create openai_org --project ${GCLOUD_PROJECT} --data-file=-
	# gcloud beta secrets add-iam-policy-binding openai_org --project ${GCLOUD_PROJECT} --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor
	
	printf ${HUGGINGFACE_TOKEN} | gcloud secrets create huggingface_token --project ${GCLOUD_PROJECT} --data-file=-
	gcloud beta secrets add-iam-policy-binding huggingface_token --project ${GCLOUD_PROJECT} --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor

	# gcloud secrets create service_account_dev --project ${GCLOUD_PROJECT} --data-file=${SVC_DEV_PATH}
	# gcloud beta secrets add-iam-policy-binding service_account_dev --project ${GCLOUD_PROJECT} --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor

	# gcloud secrets create service_account_prod --project ${GCLOUD_PROJECT} --data-file=${SVC_PROD_PATH}
	# gcloud beta secrets add-iam-policy-binding service_account_prod --project ${GCLOUD_PROJECT} --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
