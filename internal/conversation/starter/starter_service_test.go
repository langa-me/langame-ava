package starter

import (
	"testing"
)

func TestConversationStarterService_Query(t *testing.T) {
	tests := []struct {
		name   string
		input  string
		output *string
		err    error
	}{
		{
			"valid request",
			"",
			nil,
			error(nil),
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			response, err := Query("")
			if response != nil {
				if response != tt.output {
					t.Error("response: expected", tt.output, "received", response)
				}
			}

			if err != nil {
				if err != tt.err {
					t.Error("error: expected", tt.err, "received", err)
				}
			}
		})
	}
}
