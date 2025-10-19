package client

import (
	"crypto/tls"
	"net/http"
	"github.com/gocolly/colly/v2"
)
var Cookie string = ""

func NewCompatClient() *http.Client {
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify:       true,
			CipherSuites:             []uint16{tls.TLS_RSA_WITH_AES_128_CBC_SHA},
			PreferServerCipherSuites: true,
			Renegotiation:            tls.RenegotiateNever,
			VerifyConnection:         nil,
			MinVersion:               tls.VersionTLS10,
			MaxVersion:               tls.VersionTLS10,
		},
	}
	return &http.Client{
		Transport: transport,
	}
}

func SetCookie(c string) {
	Cookie = c
}

func NewArchiverCollector() *colly.Collector {
	c := colly.NewCollector(
		colly.Headers(map[string]string{
			"Cookie": Cookie,
		}),
	)
	c.SetClient(NewCompatClient())
	return c
}
