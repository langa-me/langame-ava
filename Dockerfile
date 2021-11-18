FROM golang as build

WORKDIR /app

COPY . .

# Build static binary
RUN CGO_ENABLED=0 GOOS=linux \
    go build -a -installsuffix cgo \
    -o /go/bin/server \
    cmd/server/main.go

FROM scratch

COPY --from=build /go/bin/server /server
COPY --from=build /app/config.yaml /config.yaml

ENTRYPOINT ["/server", "./config.yaml"]