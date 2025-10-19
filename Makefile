all: reid post

reid:
	@mkdir -p build/
	@go build -o build/reid_crawler ./cmd/reid/main.go

post:
	@mkdir -p build/
	@go build -o build/post_crawler ./cmd/post/main.go

.PHONY: reid post
