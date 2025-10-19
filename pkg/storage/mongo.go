package storage

import (
	"go.mongodb.org/mongo-driver/v2/mongo"
	"go.mongodb.org/mongo-driver/v2/mongo/options"
)

var mongo_addr = ""

func SetMongoAddr(addr string) {
	mongo_addr = addr
}

func newMongo() *mongo.Client {

	client, err := mongo.Connect(options.Client().ApplyURI(mongo_addr))
	if err != nil {
		panic(err)
	}
	return client
}
