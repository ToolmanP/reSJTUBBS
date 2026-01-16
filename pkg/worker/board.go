package worker

import (
	"github.com/ToolmanP/sjtubbs-archiver/pkg/client"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/storage"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/gocolly/colly/v2"
	"golang.org/x/net/html"
)

type BoardWorker struct {
	s *storage.BoardStorage
}

func NewBoardWorker() *BoardWorker {
	return &BoardWorker{
		s: storage.NewBoardStorage(),
	}
}

func (w *BoardWorker) Run() error {
	c := client.NewArchiverCollector()
	parse_payload := func(nodes []*html.Node) string {
		board := nodes[1].FirstChild.FirstChild.Data
		return board
	}
	var err error
	c.OnHTML("tbody", func(e *colly.HTMLElement) {
		for _, tr := range e.DOM.Find("tr").Nodes[1:] {
			nodes := []*html.Node{}
			for td := range tr.ChildNodes() {
				nodes = append(nodes, td)
			}
			payload := parse_payload(nodes)
			if err = w.s.Add(payload); err != nil {
				return
			}
			if err = w.s.SetStatus(payload, storage.EMPTY); err != nil {
				return
			}
		}
	})
	VisitWithRetry(c, utils.BoardURL())
	return err
}

func (w *BoardWorker) Close() {
	w.s.Close()
}

