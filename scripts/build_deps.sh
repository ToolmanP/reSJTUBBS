#!/bin/bash

set -e

if [[ ! -f "${ROOT}"/deps/go/bin/go ]]; then
bash << EOF
cd ${ROOT}/deps/go/src
./make.bash
EOF
fi

if [[ ! -f "${ROOT}/.venv" ]]; then
  uv venv && uv sync
fi
