package storage

import (
	"context"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/redis/rueidis"
)

type BoardStorage struct {
	c rueidis.Client
}

func NewBoardStorage() *BoardStorage {
	return &BoardStorage{
		c: newRedis(),
	}
}

func (s *BoardStorage) Key() string {
	return "BoardStorage"
}

func (s *BoardStorage) Add(section string) error {
	cmd := s.c.B().Sadd().Key(s.Key()).Member(section).Build()
	_, err := s.c.Do(context.Background(), cmd).AsInt64()
	return err
}

func (s *BoardStorage) LoadList() ([]string, error) {
	cmd := s.c.B().Smembers().Key(s.Key()).Build()
	sl, err := s.c.Do(context.Background(), cmd).AsStrSlice()
	if err != nil {
		return nil, err
	}
	return sl, nil
}

func (s *BoardStorage) LoadSet() (*utils.Set, error) {
	cmd := s.c.B().Smembers().Key(s.Key()).Build()
	sl, err := s.c.Do(context.Background(), cmd).AsStrSlice()
	if err != nil {
		return nil, err
	}
	return utils.NewSet(sl...), nil
}

func (s *BoardStorage) Remove(sections ...string) error {
	cmd := s.c.B().Srem().Key(s.Key()).Member(sections...).Build()
	_, err := s.c.Do(context.Background(), cmd).AsInt64()
	return err
}

func (s *BoardStorage) In(section string) bool {
	cmd := s.c.B().Sismember().Key(s.Key()).Member(section).Build()
	f, _ := s.c.Do(context.Background(), cmd).AsBool()
	return f
}

func (s *BoardStorage) Close() {
	s.c.Close()
}
