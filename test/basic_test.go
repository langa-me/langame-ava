package test

import (
	"context"
	"fmt"
	"io"
	"log"
	"net"
	"testing"

	firebase "firebase.google.com/go"
	firebase_auth "firebase.google.com/go/auth"
	grpc_auth "github.com/grpc-ecosystem/go-grpc-middleware/auth"
	api "github.com/langa-me/langame-ava/internal/langame/ava/v1"
	"github.com/langa-me/langame-ava/internal/server"
	"google.golang.org/api/option"
	"google.golang.org/grpc"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/test/bufconn"
)

const bufSize = 1024 * 1024

var (
	lis *bufconn.Listener
	firebaseAuthentication *firebase_auth.Client
)

func init() {
	lis = bufconn.Listen(bufSize)
	ctx := context.Background()
	fb, err := firebase.NewApp(ctx, nil, option.WithCredentialsFile("../svc.dev.json"))
	if err != nil {
		panic(fmt.Sprintf("Failed to init firebase: %v", err))
	}
	fa, err := fb.Auth(ctx)
	firebaseAuthentication = fa
	server.App = fb
	if err != nil {
		panic(fmt.Sprintf("Failed to init firebase auth: %v", err))
	}
	s := grpc.NewServer(
		grpc.StreamInterceptor(grpc_auth.StreamServerInterceptor(server.AuthFunc)),
	)
	api.RegisterAvaServer(s, server.NewServer())
	go func() {
		if err := s.Serve(lis); err != nil {
			log.Fatalf("Server exited with error: %v", err)
		}
	}()
}

func bufDialer(context.Context, string) (net.Conn, error) {
	return lis.Dial()
}

func Test_SayHello(t *testing.T) {
	ctx := context.Background()
	conn, err := grpc.DialContext(ctx, "bufnet", grpc.WithContextDialer(bufDialer), grpc.WithInsecure())
	if err != nil {
		t.Fatalf("Failed to dial bufnet: %v", err)
	}
	defer conn.Close()
	client := api.NewAvaClient(conn)
	stream, err := client.Stream(ctx)
	if err != nil {
		t.Fatalf("stream failed: %v", err)
	}
	waitc := make(chan struct{})
	go func() {
		for {
			_, err := stream.Recv()
			if err == io.EOF {
				// read done.
				close(waitc)
				return
			}
			// Expect not authencated error
			if err == nil {
				log.Fatalf("should have been non authenticated : %v", err)
			}
		}
	}()
	err = stream.Send(&api.StreamAvaRequest{
		Message: "Hello, World!",
	})
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	stream.CloseSend()
	<-waitc
}



func Test_Auth(t *testing.T) {
	// Throw not implemented, TODO: auth with api key
	panic("Not implemented")
	sci := func (authFunc grpc_auth.AuthFunc) grpc.StreamClientInterceptor {
		return func(ctx context.Context, desc *grpc.StreamDesc,
			cc *grpc.ClientConn, method string, streamer grpc.Streamer,
			opts ...grpc.CallOption) (grpc.ClientStream, error) {
			return streamer(ctx, desc, cc, method, opts...)
		}
	}

	ctx := context.Background()
	token, err := firebaseAuthentication.CustomToken(ctx, "test")
	if err != nil {
		t.Fatalf("Failed to create token: %v", err)
	}
	ctx = metadata.AppendToOutgoingContext(ctx, "authorization", fmt.Sprintf("bearer %s", token))
	at := func (ctx context.Context) (context.Context, error) {
		return metadata.AppendToOutgoingContext(ctx, "authorization", token), nil
	}
	conn, err := grpc.DialContext(ctx, "bufnet", grpc.WithContextDialer(bufDialer),
		grpc.WithInsecure(),
		grpc.WithStreamInterceptor(sci(at)),
	)
	if err != nil {
		t.Fatalf("Failed to dial bufnet: %v", err)
	}
	defer conn.Close()
	client := api.NewAvaClient(conn)
	stream, err := client.Stream(ctx)
	if err != nil {
		t.Fatalf("stream failed: %v", err)
	}
	waitc := make(chan struct{})
	go func() {
		for {
			in, err := stream.Recv()
			if err == io.EOF {
				// read done.
				close(waitc)
				return
			}
			if err != nil {
				log.Fatalf("Failed to receive : %v", err)
			}
			log.Printf("Got message %s", in.CallInfo)
		}
	}()
	err = stream.Send(&api.StreamAvaRequest{
		Message: "Hello, World!",
	})
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	stream.CloseSend()
	<-waitc
}
