#!/bin/bash

export AWS_PROFILE="prod"
export AWS_REGION="us-east-1"
if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="cf-templates-5d0x5unchag-us-east-2"
    AWS_REGION="us-east-2"
fi

version="1.0.14"

echo "Creating package.yaml"
sam package --template-file template_v2.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged.yaml --s3-prefix "guarddutybenchmark/v"$version --region $AWS_REGION --profile $AWS_PROFILE

echo "Publishing sumologic-guardduty-benchmark "$version
sam publish --template packaged.yaml --region $AWS_REGION --semantic-version $version

echo "Published sumologic-guardduty-benchmark "$version
# sam deploy --template-file packaged_sumo_app_utils.yaml --stack-name testingsumoapputils --capabilities CAPABILITY_IAM --region $AWS_REGION