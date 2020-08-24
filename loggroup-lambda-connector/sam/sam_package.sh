#!/bin/bash

if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="cf-templates-5d0x5unchag-us-east-2"
    AWS_REGION="us-east-2"
fi

version="1.0.3"

sam package --template-file template.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged.yaml --s3-prefix "LoggroupConnector/v$version"

sam deploy --template-file packaged.yaml --stack-name testingloggrpconnector --capabilities CAPABILITY_IAM --region $AWS_REGION  --parameter-overrides LambdaARN="arn:aws:lambda:us-east-1:956882708938:function:SumoCWLogsLambda" LogGroupTags="env=prod,name=apiassembly" LogGroupPattern="test"

# sam publish --template packaged.yaml --region $AWS_REGION --semantic-version $version
# aws cloudformation describe-stack-events --stack-name testingloggrpconnector --region $AWS_REGION
# aws cloudformation get-template --stack-name testingloggrpconnector  --region $AWS_REGION

