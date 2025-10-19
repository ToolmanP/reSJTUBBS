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
		log.Fatal(err)
	}

	client.SetCookie(config.Cookie)
	storage.SetRedisAddr(config.Redis)

	if len(os.Args) != 2 {
		log.Fatalln("Incorrect Input")
	}

	wg, err := worker.NewReidWorkerGroup(os.Args[1])

	if err != nil {
		log.Fatal(err)
	}

	defer wg.Close()

	if err := wg.Run(); err != nil {
		log.Fatal(err)
	}
}
