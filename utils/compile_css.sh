#!/bin/bash
#
# To install lessc:
#
# OSX:
#  - install Homebrew ('ruby -e "$(curl -fsSL https://raw.github.com/mxcl/homebrew/go)"')
#  - install node.js ('brew install node')
#  - install npm ('curl https://npmjs.org/install.sh | sh')
#  - install less ('npm install -g less')
#

pushd sngconnect/static/wuxia
lessc less/style.less > css/sngconnect.css
popd

