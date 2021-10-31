OUT=internal/djinn
OUT_DART=../langame-app/lib/models/djinn

proto:
	rm -rf ${OUT} ${OUT_DART}
	mkdir -p ${OUT} ${OUT_DART}

	protoc --go_out=. --go-grpc_out=. --dart_out=grpc:${OUT_DART} djinn.proto

build:
	go build -o bin/djinn cmd/djinn/main.go

run:
	go run cmd/djinn/main.go

docker:
	gcloud builds submit --tag IMAGE_URL