#!/bin/bash

if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="cf-templates-5d0x5unchag-us-east-2"
    AWS_REGION="us-east-2"
fi
uid=$(cat /dev/random | LC_CTYPE=C tr -dc "[:lower:]" | head -c 6)

version="1.0.11"

sam package --template-file template.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged.yaml --s3-prefix "cloudtrailbenchmark/v$version"

sam publish --template packaged.yaml --region $AWS_REGION --semantic-version $version


ACCESS_ID=""
ACCESS_KEY=""
ORG_ID=""
SUMO_DEPLOYMENT="us1"
# DEP_TYPE="App-SumoResources-CloudTrail-S3Bucket"
DEP_TYPE="Only-App"
# DEP_TYPE="App-SumoResources"

# test all only
# sam deploy --template-file packaged.yaml --stack-name testingctbenchmarkall --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --region $AWS_REGION --parameter-overrides SumoDeployment="us1" SumoAccessID="$ACCESS_ID" SumoAccessKey="$ACCESS_KEY" DeploymentType="$DEP_TYPE" SumoOrganizationID="$ORG_ID" CloudTrailTargetS3BucketName="cloudtraillogsmsyuhw"$uid SourceCategoryName="cloudtrail_bm_logs" RemoveSumoResourcesOnDeleteStack="true"


# only app
# sam deploy --template-file packaged.yaml --stack-name testingctbenchmarktr3 --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --region $AWS_REGION --parameter-overrides SumoDeployment="$SUMO_DEPLOYMENT" SumoAccessID="$ACCESS_ID" SumoAccessKey="$ACCESS_KEY" DeploymentType="$DEP_TYPE" SourceCategoryName="cloudtrail_bm_logs" RemoveSumoResourcesOnDeleteStack="true"

