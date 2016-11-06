#!/bin/bash

# This just installs prerequisites ... if you already have them installed, it is skipped
# This really isn't that portable!

if ! which py.test; then
  set -x
  sudo pip install pytest || exit 2
  set +x
fi

if ! python -c 'import bs4'; then
  set -x
  sudo pip install beautifulsoup4 || exit 2
fi

if ! which npm; then
  set -x
  if which yum; then
    sudo yum install npm || exit 2
  elif which apt-get; then
    sudo apt-get install npm || exit 2
  else
    echo "FATAL: We don't know how to install npm. Please install npm yourself"
    exit 2
  fi
  set +x
fi

if [[ ! -e ~/node_modules/broken-link-checker/bin/blc ]]; then
  set -x
  pushd ~ && npm install broken-link-checker@0.6.5 && popd
  set +x
fi

# The testing is done here
exec py.test --verbose "$@"
