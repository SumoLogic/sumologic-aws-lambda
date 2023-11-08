#!/bin/bash

if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="appstore-20231108-securityhub-collector"
    AWS_REGION="us-east-2"
fi
sam package --template-file template.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged.yaml

sam deploy --template-file packaged.yaml --stack-name testingsecurityhubcollector --capabilities CAPABILITY_IAM --region $AWS_REGION --parameter-overrides S3SourceBucketName=securityhubfindings
#aws cloudformation describe-stack-events --stack-name testingsecurityhublambda --region $AWS_REGION
#aws cloudformation get-template --stack-name testingsecurityhublambda  --region $AWS_REGION
# aws serverlessrepo create-application-version --region us-east-1 --application-id arn:aws:serverlessrepo:us-east-1:$AWS_ACCOUNT_ID:applications/sumologic-securityhub-connector --semantic-version 1.0.1 --template-body file://packaged.yaml
