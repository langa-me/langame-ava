package starter

import (
	"context"
	"log"

	firebase "firebase.google.com/go"
	grpc_auth "github.com/grpc-ecosystem/go-grpc-middleware/auth"
	grpc_ctxtags "github.com/grpc-ecosystem/go-grpc-middleware/tags"

	api "github.com/langa-me/langame-ava/pkg/v1/conversation/starter"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

var _ api.ConversationStarterServiceServer = (*server)(nil)
var App *firebase.App

type server struct {
	api.UnimplementedConversationStarterServiceServer
}

func NewServer() *server {
	return &server{}
}

func (*server) GetConversationStarter(ctx context.Context, req *api.ConversationStarterRequest) (*api.ConversationStarterResponse, error) {
	log.Println(req.GetInput())
 
	if req.GetInput() == "" {
		return nil, status.Errorf(codes.InvalidArgument, "input is empty")
	}
 
	return &api.ConversationStarterResponse{Output: "random"}, nil
}

/// Fetch Firestore to see if this API key is valid
func isValidApiKey(ctx context.Context, key string) (*string, error) {
	client, err := App.Firestore(context.Background())
	if err != nil {
		return nil, err
	}

	doc, err := client.Collection("users").Where("apiKeys", "array-contains", key).Limit(1).Documents(ctx).Next()

	if err != nil {
		return nil, err
	}
	return &doc.Ref.ID, nil
}

type AuthToken string

func AuthFunc(ctx context.Context) (context.Context, error) {
	token, err := grpc_auth.AuthFromMD(ctx, "bearer")
	if err != nil {
		return nil, err
	}

	uid, err := isValidApiKey(ctx, token)
	if err != nil {
		return nil, status.Errorf(codes.Unauthenticated, "invalid api key: %v", err)
	}
	
	grpc_ctxtags.Extract(ctx).Set("auth.uid", uid)

	return ctx, nil
}
