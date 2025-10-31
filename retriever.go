package main

import (
	"context"
	"log"
	"os"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/client"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/storage"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/worker"
	"github.com/urfave/cli/v3"
)

func main() {

	config, err := utils.LoadConfig()
	if err != nil {
		log.Fatal(err)
	}
	client.SetCookie(config.Cookie)
	storage.SetRedisAddr(config.Redis)
	storage.SetMongoAddr(config.Mongo)

	cmd := &cli.Command{
		Commands: []*cli.Command{
			{
				Name:  "boards",
				Usage: "Board Initialization",
				Action: func(ctx context.Context, cmd *cli.Command) error {
					w := worker.NewBoardWorker()
					defer w.Close()
					return w.Run()
				},
			},
			{
				Name:  "reids",
				Usage: "Caching reids from given board name.",
				Flags: []cli.Flag{
					&cli.StringSliceFlag{
						Name:     "boards",
						Aliases:  []string{"b"},
						Required: true,
						Usage:    "Boards that needs to be targeted.",
					},
					&cli.IntFlag{
						Name:     "nthreads",
						Aliases:  []string{"-t"},
						Usage:    "Multithread count.",
						Local:    false,
						Required: true,
					},
				},
				Action: func(ctx context.Context, cmd *cli.Command) error {
					worker.SetNthreads(cmd.Int("nthreads"))
					for _, board := range cmd.StringSlice("boards") {
						if err := func() error {
							wg, err := worker.NewReidWorkerGroup(board)
							if err != nil {
								return err
							}
							defer wg.Close()
							return wg.Run()
						}(); err != nil {
							return err
						}
					}
					return nil
				},
			},
			{
				Name:  "posts",
				Usage: "Fetching posts from the given names.",
				Flags: []cli.Flag{
					&cli.StringSliceFlag{
						Name:     "boards",
						Aliases:  []string{"b"},
						Required: true,
						Usage:    "Boards that needs to be targeted.",
					},
					&cli.BoolFlag{
						Name:     "reid",
						Aliases:  []string{"r"},
						Required: false,
						Usage:    "Fetch the reids before pulling the posts.",
					},
					&cli.IntFlag{
						Name:     "nthreads",
						Aliases:  []string{"-t"},
						Usage:    "Multithread count.",
						Local:    false,
						Required: true,
					},
				},
				Action: func(ctx context.Context, cmd *cli.Command) error {
					f := cmd.Bool("reid")
					worker.SetNthreads(cmd.Int("nthreads"))
					for _, board := range cmd.StringSlice("boards") {

						if f {
							if err := func() error {
								wg, err := worker.NewReidWorkerGroup(board)
								if err != nil {
									return err
								}
								defer wg.Close()
								return wg.Run()
							}(); err != nil {
								return err
							}
						}

						if err := func() error {
							wg, err := worker.NewPostWorkerGroup(board)
							if err != nil {
								return err
							}
							defer wg.Close()
							return wg.Run()
						}(); err != nil {
							return err
						}
					}
					return nil
				},
			},
		},
	}
	if err := cmd.Run(context.Background(), os.Args); err != nil {
		log.Fatal(err)
	}
}
