#!/usr/bin/env bash

# https://docs.docker.com/engine/reference/commandline/images/

echo NOTE: Docker will warn you if any containers exist that are using these untagged images.
echo "  So you can safely ignore any printed errors ..."
echo

# ditto for containers which take space
docker ps -f status=exited -q | xargs --no-run-if-empty docker rm

# ditto for images
docker images -f "dangling=true" -q | xargs --no-run-if-empty docker rmi

# ditto for volumes which also take space
docker volume ls -f dangling=true -q | xargs --no-run-if-empty docker volume rm

