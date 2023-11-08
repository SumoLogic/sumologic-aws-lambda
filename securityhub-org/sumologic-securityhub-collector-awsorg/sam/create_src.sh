#!/bin/bash

mkdir src
ret=$?
cd src
cp -r ../../src/  .
if [ "$ret" == "1" ]
then
    echo "package_dir present"
else
    echo "package_dir created"
    pip install -r ../requirements.txt -t ./
    chmod -R 755 .
fi

rm -r ../src/src.zip
zip -r ../src/src.zip .

unzip -l ../src.zip | grep "src"
cd ..
echo "please delete sam/src directory manually"
