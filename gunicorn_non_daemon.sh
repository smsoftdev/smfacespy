#!/bin/bash
pushd .
cd src
gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:9090 --workers 2
popd
