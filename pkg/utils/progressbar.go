package utils

import "github.com/cheggaaa/pb/v3"

var bar_tmpl = `{{string . "prefix"}}: {{ bar . "<" "-" "->" "." "."}} {{speed . }} {{percent .}}`

func NewProgressBar(total int, prefix string) *pb.ProgressBar {
	bar := pb.New(total).SetTemplateString(bar_tmpl).Set("prefix", prefix)
	return bar
}
