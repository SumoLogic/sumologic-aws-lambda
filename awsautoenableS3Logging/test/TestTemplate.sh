#!/bin/sh

export AWS_REGION="ap-south-1"
export AWS_PROFILE="personal"
# App to test
export AppName="tag"
export InstallTypes=("s3" "s3exiting" "vpc" "vpcexisting" "alb" "albexisting")

export BucketName="sumologiclambdahelper-${AWS_REGION}"
export FilterExpression=".*"

for InstallType in "${InstallTypes[@]}"
do
    export BucketPrefix=${InstallType}"-LOGS/"

    if [[ "${InstallType}" == "s3" ]]
    then
        export EnableLogging="S3"
        export TaggingResourceOptions="New"
    elif [[ "${InstallType}" == "s3exiting" ]]
    then
        export EnableLogging="S3"
        export TaggingResourceOptions="Existing"
    elif [[ "${InstallType}" == "vpc" ]]
    then
        export EnableLogging="VPC"
        export TaggingResourceOptions="New"
    elif [[ "${InstallType}" == "vpcexisting" ]]
    then
        export EnableLogging="VPC"
        export TaggingResourceOptions="Existing"
    elif [[ "${InstallType}" == "alb" ]]
    then
        export EnableLogging="ALB"
        export TaggingResourceOptions="New"
    elif [[ "${InstallType}" == "albexisting" ]]
    then
        export EnableLogging="ALB"
        export TaggingResourceOptions="Existing"
        export BucketPrefix=${InstallType}"-LOGS"
    else
        echo "No Valid Choice."
    fi

    # Stack Name
    export stackName="${AppName}-${InstallType}"

    aws cloudformation deploy --region ${AWS_REGION} --profile ${AWS_PROFILE} --template-file ././../auto_enable_s3_alb.template.yaml \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides EnableLogging="${EnableLogging}" TaggingResourceOptions="${TaggingResourceOptions}" \
    FilterExpression="${FilterExpression}" BucketName="${BucketName}" BucketPrefix="${BucketPrefix}" &

    export ExistingResource="No"

done
