package storage

import (
	"context"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/models"
	"go.mongodb.org/mongo-driver/v2/bson"
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

type PostStorage struct {
	c       *mongo.Collection
	section string
}

func NewPostStorage(section string) *PostStorage {
	m := newMongo()
	c := m.Database("sjtubbs").Collection(section)
	c.Indexes().CreateOne(context.Background(), mongo.IndexModel{
		Keys:    bson.D{{Key: "reid", Value: 1}},
		Options: options.Index().SetUnique(true),
	})
	return &PostStorage{
		c:       c,
		section: section,
	}
}

func (s *PostStorage) InsertPost(post *models.Post) error {
	ctx := context.Background()
	_, err := s.c.InsertOne(ctx, post)
	return err
}

func (s *PostStorage) Close() {
	err := s.c.Database().Client().Disconnect(context.Background())
	if err != nil {
		panic(err)
	}
}
