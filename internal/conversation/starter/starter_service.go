package starter

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
)

var (
	API_URL = "https://SOMETHING"
)

func Query(payload string) (*string, error) {
	values := map[string]string{"inputs": payload}
	json_data, err := json.Marshal(values)

	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", API_URL, bytes.NewReader(json_data))
	if err != nil {
		return nil, err
	}
	req.Header = http.Header{
		"Content-Type":  []string{"application/json"},
	}
	client := &http.Client{}
	resp, err := client.Do(req)

	if err != nil {
		return nil, err
	}
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("%s", resp.Status)
	}

	defer resp.Body.Close()
	var parsedResponse response
	if err := json.NewDecoder(resp.Body).Decode(&parsedResponse); err != nil {
		return nil, err
	}

	fmt.Printf("log %v", parsedResponse.Output)

	return &parsedResponse.Output, nil
}

type response struct {
	Output string  `json:"output"`
}