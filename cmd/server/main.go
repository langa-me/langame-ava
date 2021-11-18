package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"

	firebase "firebase.google.com/go"
	"github.com/grpc-ecosystem/go-grpc-middleware"
	"github.com/grpc-ecosystem/go-grpc-middleware/auth"
	"github.com/grpc-ecosystem/go-grpc-middleware/logging/zap"
	"github.com/grpc-ecosystem/go-grpc-middleware/tags"
	"github.com/grpc-ecosystem/go-grpc-prometheus"
	"github.com/improbable-eng/grpc-web/go/grpcweb"
	"github.com/langa-me/langame-ava/internal/config"
	api "github.com/langa-me/langame-ava/pkg/v1/conversation/starter"
	"github.com/langa-me/langame-ava/internal/conversation/starter"
	"go.uber.org/zap"
	"google.golang.org/grpc"
)

func main() {
	var configPath = flag.String("config_path", "config.yaml", "Path to the configuration file")
	var disableAuth = flag.Bool("no_auth", false, "Whether to disable authentication")
	flag.Parse()

	log.Printf("Loading config at path %s", *configPath)
	err := config.InitConfig(*configPath)
	if err != nil {
		log.Fatalf("Failed to init config: %v", err)
	}
	log.Printf("Config loaded")
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	grpcEndpoint := fmt.Sprintf(":%s", port)
	log.Printf("gRPC endpoint [%s]", grpcEndpoint)

	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("Failed to init logger: %v", err)
	}
	defer logger.Sync() // flushes buffer, if any

	grpcServer := grpc.NewServer(
		grpc.StreamInterceptor(grpc_middleware.ChainStreamServer(
			grpc_prometheus.StreamServerInterceptor,
			grpc_ctxtags.StreamServerInterceptor(),
			grpc_zap.StreamServerInterceptor(logger),
			grpc_auth.StreamServerInterceptor(starter.AuthFunc)),
		),
		grpc.UnaryInterceptor(grpc_middleware.ChainUnaryServer(
			grpc_prometheus.UnaryServerInterceptor,
			grpc_ctxtags.UnaryServerInterceptor(),
			grpc_zap.UnaryServerInterceptor(logger),
			grpc_auth.UnaryServerInterceptor(starter.AuthFunc)),
		),
	)
	// Override the default gRPC server with our unauthenticated server
	if disableAuth != nil && *disableAuth {
		grpcServer = grpc.NewServer()
		log.Printf("Authentication is disabled")
	}
	ctx := context.Background()
	fb, err := firebase.NewApp(ctx, &firebase.Config{
		ProjectID: "langame-dev",
	})
	starter.App = fb
	if err != nil {
		panic(fmt.Sprintf("Failed to init firebase: %v", err))
	}
	api.RegisterConversationStarterServiceServer(grpcServer, starter.NewServer())

	wrappedGrpc := grpcweb.WrapServer(grpcServer)
	if err := http.ListenAndServe(":"+port, http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*") // The CORS header to make it work also on our custom domain in the GCP environment
		w.Header().Set("Access-Control-Allow-Methods", "*")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		wrappedGrpc.ServeHTTP(w, req) // gRPC Web server handling the request
	})); err != nil {
		panic(err)
	}
}
