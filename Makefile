REGISTRY ?= gcr.io/langame-dev/conversation-starter
VERSION ?= latest-dev
GATEWAY_FLAGS := -I ./proto -I include/googleapis -I include/grpc-gateway
OPENAI_KEY ?= foo
OPENAI_ORG ?= bar
SVC_DEV_PATH ?= "../svc.dev.json"
SVC_PROD_PATH ?= "../svc.prod.json"
GCLOUD_PROJECT:=$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)
GCP_RUN_SVC:=$(shell gcloud iam service-accounts list --filter="Default compute service account" --format 'value(email)' 2>/dev/null)

docker_build: ## TODO
	docker build -t ${REGISTRY}:${VERSION} . -f ./Dockerfile

docker_run: ## TODO
	docker run -p 8080:8080 \
		-v $(shell pwd)/svc.dev.json:/etc/secrets/primary/svc.json \
		-v $(shell pwd)/data:/.cache \
		-e OPENAI_KEY=${OPENAI_KEY} \
		-e OPENAI_ORG=${OPENAI_ORG} \
		${REGISTRY}:${VERSION} --fix_grammar False

deploy_run: docker_build ## [Local development] deploy to GCP.
	docker push ${REGISTRY}:${VERSION}
	gcloud run deploy conversation-starter \
		--image ${REGISTRY}:${VERSION} \
		--region us-central1 \
		--set-secrets "/etc/secrets/primary/svc.json=service_account_dev:1" \
		--set-secrets "OPENAI_KEY=openai_key:1" \
		--set-secrets "OPENAI_ORG=openai_org:1" \
		--allow-unauthenticated \
		--memory=2Gi \
		--use-http2 \
		--max-instances=5

create_svc_in_k8s: ## [Local development] create service account in Kubernetes.
	kubectl create namespace ava
	kubectl create secret generic google-cloud-service-account --from-file=svc.json=./svc.dev.json -n ava

deploy_k8s: ## [Local development] deploy to Kubernetes.
	helm install ava helm -f helm/values-dev.yaml -n ava --create-namespace

undeploy_k8s: ## [Local development] undeploy from Kubernetes.
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
	
	printf ${OPENAI_KEY} | gcloud secrets create openai_key --data-file=-
	gcloud beta secrets add-iam-policy-binding openai_key --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor

	printf ${OPENAI_ORG} | gcloud secrets create openai_org --data-file=-
	gcloud beta secrets add-iam-policy-binding openai_org --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor
	
	gcloud secrets create service_account_dev --data-file=${SVC_DEV_PATH}
	gcloud beta secrets add-iam-policy-binding service_account_dev --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor

	gcloud secrets create service_account_prod --data-file=${SVC_PROD_PATH}
	gcloud beta secrets add-iam-policy-binding service_account_prod --member="serviceAccount:${GCP_RUN_SVC}" --role=roles/secretmanager.secretAccessor

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
