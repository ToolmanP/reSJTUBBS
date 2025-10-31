package utils

import "fmt"

const (
	ORDINAL_TEMPLATE    = "https://bbs.sjtu.edu.cn/bbstdoc,board,%s,page,%d.html"
	SUBORDINAL_TEMPLATE = "https://bbs.sjtu.edu.cn/bbstcon,board,%s,reid,%s,page,%d.html"
	INITIAL_TEMPLATE    = "https://bbs.sjtu.edu.cn/bbstdoc,board,%s.html"
	BOARD_URL = "https://bbs.sjtu.edu.cn/bbsall"
)

func BuildInitialURL(section string) string {
	return fmt.Sprintf(INITIAL_TEMPLATE, section)
}

func BuildOrdinalURL(section string, page int) string {
	return fmt.Sprintf(ORDINAL_TEMPLATE, section, page)
}

func BuildSubordinalURL(section string, reid string,  page int) string {
	return fmt.Sprintf(SUBORDINAL_TEMPLATE, section, reid, page)
}

func BoardURL() string {
	return BOARD_URL
}
