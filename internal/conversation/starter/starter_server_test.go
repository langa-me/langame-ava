package starter

import (
	"context"
	"fmt"
	"log"
	"net"
	"testing"

	firebase "firebase.google.com/go"
	grpc_auth "github.com/grpc-ecosystem/go-grpc-middleware/auth"
	api "github.com/langa-me/langame-ava/pkg/v1/conversation/starter"
	"google.golang.org/api/option"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"
)

func dialer() func(context.Context, string) (net.Conn, error) {
	listener := bufconn.Listen(1024 * 1024)
 
	ctx := context.Background()
	fb, err := firebase.NewApp(ctx, nil, option.WithCredentialsFile("../svc.dev.json"))
	if err != nil {
		panic(fmt.Sprintf("Failed to init firebase: %v", err))
	}
	App = fb
	if err != nil {
		panic(fmt.Sprintf("Failed to init firebase auth: %v", err))
	}
	s := grpc.NewServer(
		grpc.StreamInterceptor(grpc_auth.StreamServerInterceptor(AuthFunc)),
	)
	api.RegisterConversationStarterServiceServer(s, NewServer())
 
	go func() {
		if err := s.Serve(listener); err != nil {
			log.Fatal(err)
		}
	}()
 
	return func(context.Context, string) (net.Conn, error) {
		return listener.Dial()
	}
}
 
func TestConversationStarterServer_GetConversationStarter(t *testing.T) {
	tests := []struct {
		name    string
		input  string
		res     *api.ConversationStarterResponse
		errCode codes.Code
		errMsg  string
	}{
		{
			"valid request",
			"",
			nil,
			codes.InvalidArgument,
			"input is empty",
		},
	}
 
	ctx := context.Background()
 
	conn, err := grpc.DialContext(ctx, "", grpc.WithInsecure(), grpc.WithContextDialer(dialer()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
 
	client := api.NewConversationStarterServiceClient(conn)
 
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			request := &api.ConversationStarterRequest{Input: tt.input}
 
			response, err := client.GetConversationStarter(ctx, request)
 
			if response != nil {
				if response.GetOutput() != tt.res.GetOutput() {
					t.Error("response: expected", tt.res.GetOutput(), "received", response.GetOutput())
				}
			}
 
			if err != nil {
				if er, ok := status.FromError(err); ok {
					if er.Code() != tt.errCode {
						t.Error("error code: expected", codes.InvalidArgument, "received", er.Code())
					}
					if er.Message() != tt.errMsg {
						t.Error("error message: expected", tt.errMsg, "received", er.Message())
					}
				}
			}
		})
	}
}
