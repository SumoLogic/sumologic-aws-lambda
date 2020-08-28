#!/bin/bash

if [ "$AWS_PROFILE" != "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="cf-templates-5d0x5unchag-us-east-2"
    AWS_REGION="us-east-2"
fi

rm src/external/*.pyc
rm src/*.pyc
rm sumo_app_utils.zip

if [ ! -f sumo_app_utils.zip ]; then
    echo "creating zip file"
    mkdir python
    cd python
    pip install  crhelper -t .
    pip install requests -t .
    pip install retrying -t .
    cp -v ../src/*.py .
    zip -r ../sumo_app_utils.zip .
    cd ..
    rm -r python
fi

version="2.0.3"

aws s3 cp sumo_app_utils.zip s3://$SAM_S3_BUCKET/sumo_app_utils/v"$version"/sumo_app_utils.zip --region $AWS_REGION --acl public-read

sam package --template-file sumo_app_utils.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged_sumo_app_utils.yaml --s3-prefix "sumo_app_utils/v"$version

sam publish --template packaged_sumo_app_utils.yaml --region $AWS_REGION --semantic-version $version
# sam deploy --template-file packaged_sumo_app_utils.yaml --stack-name testingsumoapputils --capabilities CAPABILITY_IAM --region $AWS_REGION

