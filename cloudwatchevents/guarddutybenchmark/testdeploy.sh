#!/bin/bash

if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="cf-templates-5d0x5unchag-us-east-2"
    AWS_REGION="us-east-2"
fi

version="1.0.10"

sam package --template-file template_v2.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged_v2.yaml --s3-prefix "guarddutybenchmark/v$version"

sam publish --template packaged_v2.yaml --region $AWS_REGION --semantic-version $version


ACCESS_ID=""
ACCESS_KEY=""
ORG_ID=""

SUMO_DEPLOYMENT="us1"

# sam deploy --template-file packaged_v2.yaml --stack-name testinggdbenchmarknew --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --region $AWS_REGION --parameter-overrides SumoDeployment="$SUMO_DEPLOYMENT" SumoAccessID="$ACCESS_ID" SumoAccessKey="$ACCESS_KEY" RemoveSumoResourcesOnDeleteStack="true"

