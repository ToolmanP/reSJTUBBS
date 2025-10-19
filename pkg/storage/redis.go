package storage

import "github.com/redis/rueidis"


var redis_addr = ""
func SetRedisAddr(addr string) {
	redis_addr = addr
}
func newRedis() rueidis.Client {
	c, err := rueidis.NewClient(rueidis.ClientOption{
		InitAddress: []string{redis_addr},
	})
	if err != nil {
		panic(err)
	}
	return c
}
