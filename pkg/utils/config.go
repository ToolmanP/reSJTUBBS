package utils

import (
	"github.com/spf13/viper"
)

type ArchiverConfig struct {
	Cookie string `yaml:"cookie"`
	Redis   string `yaml:"redis"`
	Mongo   string `yaml:"mongo"`
}

func LoadConfig() (*ArchiverConfig, error) {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")

	if err := viper.ReadInConfig(); err != nil {
		return nil, err
	}

	c := &ArchiverConfig{}
	if err := viper.Unmarshal(c); err != nil {
		return nil, err
	}

	return c, nil
}
