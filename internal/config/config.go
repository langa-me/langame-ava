package config

import (
	"os"

	"gopkg.in/yaml.v2"
)

var Config *config

type config struct {
    HuggingfaceKey string `yaml:"huggingface_key"`
}

func InitConfig(configPath string) error {
	f, err := os.Open(configPath)
	if err != nil {
		return err
	}
	defer f.Close()

	decoder := yaml.NewDecoder(f)
	err = decoder.Decode(&Config)
	if err != nil {
		return err
	}
	return nil
}