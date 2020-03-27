#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="auto_enable_s3_alb"
export AppName="alb"
export InstallTypes=("all")

for InstallType in "${InstallTypes[@]}"
do
    export BucketName="alb-apps3sources3bucket123-qwerty"
    export EnableS3LoggingALBResources="Yes"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../sam/${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides BucketName="${BucketName}" EnableS3LoggingALBResources="${EnableS3LoggingALBResources}" AccountAlias="test"

done

echo "All Installation Complete for ${AppName}"