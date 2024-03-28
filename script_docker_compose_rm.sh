#!/bin/bash

docker container rm -f container_FUMI2 container_postgres_FUMI2
docker image rm -f src-app src-db
