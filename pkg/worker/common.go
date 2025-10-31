package worker

import (
	"runtime"
	"time"

	"github.com/gocolly/colly/v2"
)

var nthreads = 0
var wait_interval = 1 * time.Second

func init() {
	nthreads = runtime.NumCPU()
}

func VisitWithRetry(c *colly.Collector, url string) {
	var err error
	for {
		if err = c.Visit(url); err == nil {
			break
		} else {
			time.Sleep(wait_interval)
		}
	}
}
