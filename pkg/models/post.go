package models

type Post struct {
	Reid      string    `bson:"reid"`
	Title     string    `bson:"title"`
	Pages     []string  `bson:"pages"`
	Section   string    `bson:"section"`
}
