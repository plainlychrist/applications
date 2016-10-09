#!/bin/bash

if ! which py.test; then
  set -x
  sudo yum install python27-pytest
  set +x
fi

py.test
