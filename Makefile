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


GATEWAY_FLAGS := -I ./proto -I include/googleapis -I include/grpc-gateway


zz:
	mkdir -p openapiv2/
	protoc $(GATEWAY_FLAGS) \
		--openapiv2_out ./openapiv2 --openapiv2_opt logtostderr=true \
		proto/ava/v1/*.proto
	python3 -m grpc_tools.protoc $(GATEWAY_FLAGS) --python_out=. --grpc_python_out=. proto/ava/v1/*.proto

gw:
	protoc $(GATEWAY_FLAGS) \
		--go_out=Mgoogle/api/annotations.proto=github.com/grpc-ecosystem/grpc-gateway/third_party/googleapis/google/api,plugins=grpc:. \
		--grpc-gateway_out=logtostderr=true:. \
		*.proto

deps:
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
	go install \
		github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest \
		github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2@latest \
		github.com/grpc-ecosystem/grpc-gateway/protoc-gen-swagger@latest \
		google.golang.org/protobuf/cmd/protoc-gen-go@latest \
		google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest


install: ## [Local development] Upgrade pip, install requirements, install package.
	python3 -m virtualenv env
	source env/bin/activate
	python3 -m pip install -U pip
	python3 -m pip install -e .
	python3 -m pip install -r requirements-test.txt


.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
