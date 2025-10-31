package worker

import (
	"errors"
	"fmt"
	"log/slog"
	"regexp"
	"strconv"
	"sync"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/client"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/models"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/storage"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/gocolly/colly/v2"
)

type PostWorkerGroup struct {
	posts   *storage.PostStorage
	reids   *storage.ReidStorage
	section string
}

func NewPostWorkerGroup(section string) (*PostWorkerGroup, error) {
	validator := storage.NewBoardStorage()
	defer validator.Close()
	if !validator.In(section) {
		return nil, errors.New("Validation Failed for board: " + section + ". Refetch the board info and validate your input.")
	}
	return &PostWorkerGroup{
		posts:   storage.NewPostStorage(section),
		reids:   storage.NewReidStorage(section),
		section: section,
	}, nil
}

func (w *PostWorkerGroup) getTotalPostPage(reid string) (int, error) {
	var fetcherr error
	c := client.NewArchiverCollector()
	p := regexp.MustCompile(`本主题共有 (\d+) 篇文章，分 (\d+) 页, 当前显示第 (\d+) 页`)
	fetcherr = nil
	pages := 0
	url := utils.BuildSubordinalURL(w.section, reid, 1)
	c.OnResponse(func(r *colly.Response) {
		matches := p.FindStringSubmatch(string(r.Body))
		if len(matches) < 3 {
			fmt.Println(string(r.Body), url)
			panic(errors.New("incorrect matches"))
		}
		t, err := strconv.Atoi(matches[2])
		if err != nil {
			fetcherr = err
			return
		}
		pages = t
	})
	VisitWithRetry(c, url)
	return pages, fetcherr
}

func (w *PostWorkerGroup) Run() error {
	reids, err := w.reids.LoadList()

	if err != nil {
		return err
	}

	bar := utils.NewProgressBar(len(reids), "Fetching Posts from "+w.section)
	var wg sync.WaitGroup
	ch := make(chan string, nthreads)
	bar.Start()
	for i := range nthreads {
		var _ = i
		wg.Go(func() {
			contents := []string{}
			c := client.NewArchiverCollector()
			c.OnResponse(func(r *colly.Response) {
				contents = append(contents, string(r.Body))
			})
			retrieve_one := func(reid string) error {
				pages, err := w.getTotalPostPage(reid)
				if err != nil {
					return err
				}
				contents = []string{}
				for page := range pages {
					VisitWithRetry(c, utils.BuildSubordinalURL(w.section, reid, page+1))
				}

				payload, err := w.reids.GetPayload(reid)
				if err != nil {
					return err
				}
				err = w.reids.Remove(reid)
				if err := w.posts.InsertPost(&models.Post{
					Reid:    reid,
					Title:   payload.Title,
					Section: w.section,
					Pages:   contents,
				}); err != nil {
					return err
				}
				return nil
			}
			for reid := <-ch; reid != ""; reid = <-ch {
				if err := retrieve_one(reid); err != nil {
					slog.Error("Failed to retrieve", "reid", reid, "board", w.section, "error", err)
				}
				bar.Increment()
			}
		})
	}

	for _, reid := range reids {
		ch <- reid
	}
	close(ch)
	wg.Wait()
	bar.Finish()
	return nil
}

func (w *PostWorkerGroup) Close() {
	w.reids.Close()
	w.posts.Close()
}
