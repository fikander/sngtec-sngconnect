#!/bin/bash

pushd sngconnect/static/wuxia
lessc less/style.less > css/sngconnect.css
popd

