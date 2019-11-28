#!/bin/bash

if [ "$AWS_PROFILE" == "prod" ]
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
    pip install -r requirements.txt -t .
    cp -v ../src/*.py .
    zip -r ../sumo_app_utils.zip .
    cd ..
    rm -r python
fi

aws s3 cp sumo_app_utils.zip s3://$SAM_S3_BUCKET/ --region $AWS_REGION

sam package --template-file sumo_app_utils.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged_sumo_app_utils.yaml

sam deploy --template-file packaged_sumo_app_utils.yaml --stack-name testingsumoapputils --capabilities CAPABILITY_IAM --region $AWS_REGION

# Before testing below command one needs to publish new version of sumo_app_utils and change version in template
sam package --template-file /Users/hpal/git/sumologic-aws-lambda/cloudwatchevents/guarddutybenchmark/template_v2.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file /Users/hpal/git/sumologic-aws-lambda/cloudwatchevents/guarddutybenchmark/packaged_v2.yaml

sam deploy --template-file /Users/hpal/git/sumologic-aws-lambda/cloudwatchevents/guarddutybenchmark/packaged_v2.yaml --stack-name guarddutysamdemo --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --region $AWS_REGION --parameter-overrides SumoAccessID=$SUMO_ACCESS_ID SumoAccessKey=$SUMO_ACCESS_KEY SumoDeployment=$SUMO_DEPLOYMENT RemoveSumoResourcesOnDeleteStack="true"

#aws cloudformation describe-stack-events --stack-name testingsecurityhublambda --region $AWS_REGION
#aws cloudformation get-template --stack-name testingsecurityhublambda  --region $AWS_REGION
# aws serverlessrepo create-application-version --region us-east-1 --application-id arn:aws:serverlessrepo:us-east-1:$AWS_ACCOUNT_ID:applications/sumologic-securityhub-connector --semantic-version 1.0.1 --template-body file://packaged.yaml
