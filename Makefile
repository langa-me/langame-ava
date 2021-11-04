VERSION ?= latest-dev

docker_build_push:
	docker build -t louis030195/ava:${VERSION} . -f ./Dockerfile
	docker tag louis030195/ava:${VERSION} louis030195/ava:${VERSION}
	docker push louis030195/ava:${VERSION}

search_docker_build_push:
	docker build -t louis030195/ava-search:${VERSION} ./search_engine -f ./search_engine/Dockerfile
	docker tag louis030195/ava-search:${VERSION} louis030195/ava-search:${VERSION}
	docker push louis030195/ava-search:${VERSION}

search_docker_run:
	docker run --rm --name ava-search louis030195/ava-search:${VERSION}