#!/bin/bash

mkdir src
ret=$?
cd src
cp -r ../../src/  .
if [ "$ret" == "1" ]
then
    echo "src/ directory present in sam/ directory"
else
    echo "src/ directory created in sam/ directory"
    pip install -r ../requirements.txt -t ./
    chmod -R 755 .
fi
rm src.zip
zip -r src.zip .
mv src.zip ../../src/src.zip
echo "please delete sam/src directory manually"
cd ..
