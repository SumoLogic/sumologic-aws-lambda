#!/bin/bash

rm src/external/*.pyc
rm src/*.pyc
rm telemetry.zip

if [ ! -f telemetry.zip ]; then
    echo "creating zip file"
    mkdir python
    cd python
    pip3 install  crhelper -t .
    pip3 install sumologic-appclient-sdk -t .
    pip3 install future_fstrings -t .
    pip3 install setuptools -t .
    cp -v ../* .
    zip -r ../telemetry.zip .
    cd ..
    rm -r python
fi
