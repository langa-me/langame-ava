# VERSION ?= latest-dev

# docker_build_push:
# 	docker build -t louis030195/ava:${VERSION} .. -f ./Dockerfile
# 	docker tag louis030195/ava:${VERSION} louis030195/ava:${VERSION}
# 	docker push louis030195/ava:${VERSION}

# search_docker_build_push:
# 	docker build -t louis030195/ava-search:${VERSION} ./search_engine -f ./search_engine/Dockerfile
# 	docker tag louis030195/ava-search:${VERSION} louis030195/ava-search:${VERSION}
# 	docker push louis030195/ava-search:${VERSION}

# search_docker_run:
# 	docker run --rm --name ava-search louis030195/ava-search:${VERSION}

# Store the protobuf installation command into a variable for use later
PROTOBUF_INSTALL = ""
UNAME := $(shell uname)

ifeq ($(UNAME),Windows)
	echo "Windows? In 2021?"
	exit 1
endif
ifeq ($(UNAME),Darwin)
	PROTOBUF_INSTALL = $(shell brew install protobuf)
endif
ifeq ($(UNAME),Linux)
	PROTOBUF_INSTALL = $(shell sudo apt install -y protobuf-compiler)
endif

OUT := pkg/v1/conversation/starter
GATEWAY_FLAGS := -I $(OUT) -I third_parties/googleapis -I third_parties/grpc-gateway

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
	openapi lint openapiv2/ava/v1/api.swagger.json || echo "Failed, might need npm i -g @redocly/openapi-cli@latest ? :)"

compile: ## [Local development] Generate protos, openapi, grpc-gateway proxy.
	mkdir -p $(OUT)
	protoc $(GATEWAY_FLAGS) \
		--openapiv2_out $(OUT) --openapiv2_opt logtostderr=true \
		--go_out=$(OUT) \
		--go-grpc_out=$(OUT) \
		--grpc-gateway_out=logtostderr=true:$(OUT) \
		$(OUT)/*.proto

deps: ## [Local development] Install dependencies.
	$(shell ${PROTOBUF_INSTALL})
	@which go > /dev/null || (echo "go need to be installed" && exit 1)
	go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest
	go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@latest
	go install github.com/grpc-ecosystem/grpc-gateway/protoc-gen-swagger@latest
	go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest


download_third_parties: ## [Local development] Download third-parties.
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
	

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
