package main

import (
	"log"
	"os"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/client"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/storage"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/worker"
)

func main() {

	config, err := utils.LoadConfig()

	if err != nil {
		panic(err)
	}

	client.SetCookie(config.Cookie)
	storage.SetRedisAddr(config.Redis)
	storage.SetMongoAddr(config.Mongo)

	if len(os.Args) != 2 {
		log.Fatalln("Incorrect Input")
	}

	w := worker.NewPostWorkerGroup(os.Args[1])

	defer w.Close()

	if err := w.Run(); err != nil {
		panic(err)
	}

}
