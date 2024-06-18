#!/bin/bash

rm src/external/*.pyc
rm src/*.pyc
rm telemetry.zip

if [ ! -f sumo_app_utils.zip ]; then
    echo "creating zip file"
    mkdir python
    cd python
    pip3 install  crhelper -t .
    pip3 install requests -t .
    pip3 install retrying -t .
    cp -v ../*.py .
    zip -r ../telemetry.zip .
    cd ..
    rm -r python
fi
