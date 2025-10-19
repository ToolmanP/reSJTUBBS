package models

import "encoding/json"

type Reid struct {
	Reid      string    `json:"reid"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Section   string    `json:"section"`
}

func (p *Reid) String() string {
	b, _ := json.Marshal(p)
	return string(b)
}
