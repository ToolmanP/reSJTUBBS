package worker

import (
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/client"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/models"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/storage"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/gocolly/colly/v2"
	"golang.org/x/net/html"
)

type ReidWorkerGroup struct {
	section string
	storage *storage.ReidStorage
	total   int
}

func FetchInitialTotal(section string) (int, error) {
	url := utils.BuildInitialURL(section)
	c := client.NewArchiverCollector()
	total := 0

	r := regexp.MustCompile(`主题(\d+)个`)

	c.OnHTML("center", func(e *colly.HTMLElement) {
		s := e.Text
		matches := r.FindStringSubmatch(s)
		t, err := strconv.Atoi(matches[1])
		if err != nil {
			panic(err)
		}
		total = t / 20
	})

	if err := c.Visit(url); err != nil {
		return total, err
	}

	return total, nil
}

func NewReidWorkerGroup(section string) (*ReidWorkerGroup, error) {

	reis_storage := storage.NewReidStorage(section)
	total, err := FetchInitialTotal(section)

	if err != nil {
		return nil, err
	}

	return &ReidWorkerGroup{
		section: section,
		storage: reis_storage,
		total:   total,
	}, nil
}

func (w *ReidWorkerGroup) Run() error {

	parse_payload := func(nodes []*html.Node) *models.Reid {
		author := nodes[2].FirstChild.FirstChild.Data
		title := nodes[4].FirstChild.FirstChild.Data[3:]
		url := nodes[4].FirstChild.Attr[0].Val
		colons := strings.Split(url, ",")
		reid := strings.Split(colons[len(colons)-1], ".")[0]
		return &models.Reid{
			Reid:    reid,
			Title:   title,
			Author:  author,
			Section: w.section,
		}
	}

	ch := make(chan int, nthreads)
	bar := utils.NewProgressBar(w.total, "Fetching Reid From "+w.section+":")
	var wg sync.WaitGroup
	bar.Start()
	for i := range nthreads {
		var _ = i
		wg.Go(
			func() {
				c := client.NewArchiverCollector()
				c.OnHTML("tbody", func(e *colly.HTMLElement) {
					for _, tr := range e.DOM.Find("tr").Nodes[1:] {
						nodes := []*html.Node{}
						for td := range tr.ChildNodes() {
							nodes = append(nodes, td)
						}
						payload := parse_payload(nodes)
						w.storage.Add(payload.Reid)
						w.storage.SetPayload(payload)
					}
				})
				for page := <-ch; page != 0; page = <-ch {
					VisitWithRetry(c, utils.BuildOrdinalURL(w.section, page-1))
					bar.Increment()
				}
				wg.Done()
			},
		)
	}

	for i := range w.total {
		ch <- i + 1
	}

	close(ch)
	wg.Wait()
	bar.Finish()
	return nil
}

func (w *ReidWorkerGroup) SetSection(section string) {
	w.section = section
}

func (w *ReidWorkerGroup) Close() {
	w.storage.Close()
}
