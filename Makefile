all: retriever

retriever:
	@mkdir -p build
	@go build -o build/retriever ./retriever.go

.PHONY: retriever
