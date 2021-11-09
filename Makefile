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

proto:
	python3 -m grpc_tools.protoc --proto_path=.  ./ava.proto --python_out=ava --grpc_python_out=ava

install: ## [Local development] Upgrade pip, install requirements, install package.
	python3 -m pip install -U pip
	python3 -m pip install -e .

install-dev: ## [Local development] Install test requirements
	python3 -m pip install -r requirements-test.txt

lint: ## [Local development] Run mypy, pylint and black
	python3 -m mypy ava
	python3 -m pylint ava
	python3 -m black --check -l 120 ava

black: ## [Local development] Auto-format python code using black
	python3 -m black -l 120 .

venv-lint-test: ## [Continuous integration]
	python3 -m venv .env && . .env/bin/activate && make install install-dev lint test && rm -rf .env

test: ## [Local development] Run unit tests
	rm -rf tests/test_folder/
	python3 -m pytest -v .45 tests

.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
