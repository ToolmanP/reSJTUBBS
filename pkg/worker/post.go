package worker

import (
	"errors"
	"fmt"
	"regexp"
	"strconv"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/client"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/models"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/storage"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/cheggaaa/pb/v3"
	"github.com/gocolly/colly/v2"
)

type PostWorkerGroup struct {
	posts   *storage.PostStorage
	reids   *storage.ReidStorage
	section string
}

func NewPostWorkerGroup(section string) *PostWorkerGroup {
	return &PostWorkerGroup{
		posts:   storage.NewPostStorage(section),
		reids:   storage.NewReidStorage(section),
		section: section,
	}
}

func (w *PostWorkerGroup) getTotalPostPage(reid string) int {
	c := client.NewArchiverCollector()
	p := regexp.MustCompile(`本主题共有 (\d+) 篇文章，分 (\d+) 页, 当前显示第 (\d+) 页`)
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
			panic(err)
		}
		pages = t
	})
	if err := c.Visit(url); err != nil {
		panic(err)
	}
	return pages
}

func (w *PostWorkerGroup) Run() error {
	reids, err := w.reids.LoadList()

	if err != nil {
		return err
	}

	c := client.NewArchiverCollector()

	contents := []string{}

	c.OnResponse(func(r *colly.Response) {
		contents = append(contents, string(r.Body))
	})

	bar := pb.StartNew(len(reids))
	for _, reid := range reids {
		pages := w.getTotalPostPage(reid)
		contents = []string{}
		for page := range pages {
			url := utils.BuildSubordinalURL(w.section, reid, page+1)
			if err := c.Visit(url); err != nil {
				return err
			}
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
		bar.Increment()
	}
	return nil
}

func (w *PostWorkerGroup) Close() {
	w.reids.Close()
	w.posts.Close()
}
