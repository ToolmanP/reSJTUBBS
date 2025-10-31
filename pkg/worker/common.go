package worker

import (
	"log/slog"
	"runtime"
	"time"

	"github.com/gocolly/colly/v2"
)

var nthreads = 4
var wait_interval = 1 * time.Second

func init() {
	nthreads = runtime.NumCPU()
}

func SetNthreads(t int) {
	nthreads = t 
}

func VisitWithRetry(c *colly.Collector, url string) {
	var err error
	for {
		if err = c.Visit(url); err == nil {
			break
		} else {
			slog.Info("Retrying the", "url", url)
			time.Sleep(wait_interval)
		}
	}
}
