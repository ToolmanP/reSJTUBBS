package utils

import "sync"

type Set struct {
	m map[string]bool
	sync.RWMutex
}

func NewSet(sl ...string) *Set {
	m := map[string]bool{}
	for _, s := range sl {
		m[s] = true
	}
	return &Set{
		m: m,
	}
}

func (s *Set) Add(item string) {
	s.Lock()
	defer s.Unlock()
	s.m[item] = true
}

func (s *Set) Remove(item string) {
	s.Lock()
	defer s.Unlock()
	delete(s.m, item)
}

func (s *Set) Has(item string) bool {
	s.RLock()
	defer s.RUnlock()
	_, ok := s.m[item]
	return ok
}

func (s *Set) Clear() {
	s.Lock()
	defer s.Unlock()
	s.m = make(map[string]bool)
}
