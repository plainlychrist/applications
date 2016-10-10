#!/bin/bash

# This just installs prerequisites ... if you already have them installed, it is skipped
# This really isn't that portable!

if ! which py.test; then
  set -x
  sudo yum install python27-pytest
  set +x
fi

if ! which npm; then
  set -x
  sudo yum install npm
  set +x
fi

if ! which npm; then
  set -x
  pushd ~ && npm install broken-link-checker@0.6.5 && popd
  set +x
fi

# The testing is done here
exec py.test --verbose
