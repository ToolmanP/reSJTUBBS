package storage

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/ToolmanP/sjtubbs-archiver/pkg/models"
	"github.com/ToolmanP/sjtubbs-archiver/pkg/utils"
	"github.com/redis/rueidis"
)

type ReidStorage struct {
	c       rueidis.Client
	section string
}

func NewReidPayloadFromBytes(b []byte) *models.Reid{
	p := &models.Reid{}
	err := json.Unmarshal(b, p)
	if err != nil {
		panic(err)
	}
	return p
}

func NewReidStorage(section string) *ReidStorage {
	c := newRedis()
	return &ReidStorage{
		c:       c,
		section: section,
	}
}

func (s *ReidStorage) WSetKey() string {
	return fmt.Sprintf("workset:reid:%s", s.section)
}

func (s *ReidStorage) PayloadKey(reid string) string {
	return fmt.Sprintf("reid:%s", reid)
}

func (s *ReidStorage) Reset() error {
	cmd := s.c.B().Del().Key(s.WSetKey()).Build()
	_, err := s.c.Do(context.Background(), cmd).AsBool()
	return err
}

func (s *ReidStorage) Add(reid ...string) error {
	cmd := s.c.B().Sadd().Key(s.WSetKey()).Member(reid...).Build()
	_, err := s.c.Do(context.Background(), cmd).AsInt64()
	return err
}

func (s *ReidStorage) LoadSet() (*utils.Set, error) {
	cmd := s.c.B().Smembers().Key(s.WSetKey()).Build()
	sl, err := s.c.Do(context.Background(), cmd).AsStrSlice()
	if err != nil {
		return nil, err
	}
	return utils.NewSet(sl...), nil
}

func (s *ReidStorage) LoadList() ([]string, error) {
	cmd := s.c.B().Smembers().Key(s.WSetKey()).Build()
	sl, err := s.c.Do(context.Background(), cmd).AsStrSlice()
	if err != nil {
		return nil, err
	}
	return sl, nil
}

func (s *ReidStorage) SetPayload(payload *models.Reid) error {
	cmd := s.c.B().Set().Key(s.PayloadKey(payload.Reid)).Value(payload.String()).Build()
	_, err := s.c.Do(context.Background(), cmd).AsBool()
	return err
}

func (s *ReidStorage) GetPayload(reid string) (*models.Reid, error) {
	cmd := s.c.B().Get().Key(s.PayloadKey(reid)).Build()
	b, err := s.c.Do(context.Background(), cmd).AsBytes()
	if err != nil {
		return nil, err
	}
	return NewReidPayloadFromBytes(b), err
}

func (s *ReidStorage) Remove(reid ...string) error {
	cmd := s.c.B().Srem().Key(s.WSetKey()).Member(reid...).Build()
	_, err := s.c.Do(context.Background(), cmd).AsInt64()
	return err
}

func (s *ReidStorage) Close() {
	s.c.Close()
}
