#!/bin/sh

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppName="tag"
export InstallTypes=("s3both" "vpcboth" "albboth")

export BucketName="sumologiclambdahelper-${AWS_REGION}"
export FilterExpression=".*"

for InstallType in "${InstallTypes[@]}"
do
    export BucketPrefix=${InstallType}"-LOGS/"

    if [[ "${InstallType}" == "s3" ]]
    then
        export AutoEnableLogging="S3"
        export AutoEnableResourceOptions="New"
    elif [[ "${InstallType}" == "s3exiting" ]]
    then
        export AutoEnableLogging="S3"
        export AutoEnableResourceOptions="Existing"
    elif [[ "${InstallType}" == "s3both" ]]
    then
        export AutoEnableLogging="S3"
        export AutoEnableResourceOptions="Both"
    elif [[ "${InstallType}" == "vpc" ]]
    then
        export AutoEnableLogging="VPC"
        export AutoEnableResourceOptions="New"
    elif [[ "${InstallType}" == "vpcexisting" ]]
    then
        export AutoEnableLogging="VPC"
        export AutoEnableResourceOptions="Existing"
    elif [[ "${InstallType}" == "vpcboth" ]]
    then
        export AutoEnableLogging="VPC"
        export AutoEnableResourceOptions="Both"
    elif [[ "${InstallType}" == "alb" ]]
    then
        export AutoEnableLogging="ALB"
        export AutoEnableResourceOptions="New"
    elif [[ "${InstallType}" == "albexisting" ]]
    then
        export AutoEnableLogging="ALB"
        export AutoEnableResourceOptions="Existing"
        export BucketPrefix=${InstallType}"-LOGS"
    elif [[ "${InstallType}" == "albboth" ]]
    then
        export AutoEnableLogging="ALB"
        export AutoEnableResourceOptions="Both"
        export BucketPrefix=${InstallType}"-BOTH"
    else
        echo "No Valid Choice."
    fi

    # Stack Name
    export stackName="${AppName}-${InstallType}"

    aws cloudformation deploy --region ${AWS_REGION} --profile ${AWS_PROFILE} --template-file ./../sumologic-s3-logging-auto-enable.yaml \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides AutoEnableLogging="${AutoEnableLogging}" AutoEnableResourceOptions="${AutoEnableResourceOptions}" \
    FilterExpression="${FilterExpression}" BucketName="${BucketName}" BucketPrefix="${BucketPrefix}" &

done
