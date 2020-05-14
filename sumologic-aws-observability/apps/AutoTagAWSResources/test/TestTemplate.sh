#!/bin/sh

export AWS_REGION="ap-south-1"
export AWS_PROFILE="personal"
# App to test
export AppName="tag"
export InstallTypes=("alb" "api" "rds" "ec2" "lambda" "dynamo" "all")

export AddTagsForALBResources="No"
export AddTagsForAPIGatewayResources="No"
export AddTagsForRDSResources="No"
export AddTagsForEC2MetricsResources="No"
export AddTagsForLambdaResources="No"
export AddTagsForDynamoDBResources="No"

for InstallType in "${InstallTypes[@]}"
do
    export AccountAlias="${AppName}${InstallType}"

    if [[ "${InstallType}" == "all" ]]
    then
        export AddTagsForALBResources="Yes"
        export AddTagsForAPIGatewayResources="Yes"
        export AddTagsForRDSResources="Yes"
        export AddTagsForEC2MetricsResources="Yes"
        export AddTagsForLambdaResources="Yes"
        export AddTagsForDynamoDBResources="Yes"
    elif [[ "${InstallType}" == "alb" ]]
    then
        export AddTagsForALBResources="Yes"
    elif [[ "${InstallType}" == "api" ]]
    then
        export AddTagsForAPIGatewayResources="Yes"
    elif [[ "${InstallType}" == "rds" ]]
    then
        export AddTagsForRDSResources="Yes"
    elif [[ "${InstallType}" == "ec2" ]]
    then
        export AddTagsForEC2MetricsResources="Yes"
    elif [[ "${InstallType}" == "lambda" ]]
    then
        export AddTagsForLambdaResources="Yes"
    elif [[ "${InstallType}" == "dynamo" ]]
    then
        export AddTagsForDynamoDBResources="Yes"
    else
        echo "No Valid Choice."
    fi

    # Stack Name
    export stackName="${AppName}-${InstallType}"

    aws cloudformation deploy --region ${AWS_REGION} --profile ${AWS_PROFILE} --template-file ././../auto_tag_resources.template.yaml \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides AddTagsForALBResources="${AddTagsForALBResources}" AddTagsForAPIGatewayResources="${AddTagsForAPIGatewayResources}" \
    AddTagsForRDSResources="${AddTagsForRDSResources}" AddTagsForEC2MetricsResources="${AddTagsForEC2MetricsResources}" \
    AddTagsForLambdaResources="${AddTagsForLambdaResources}" AccountAlias="${AccountAlias}" AddTagsForDynamoDBResources="${AddTagsForDynamoDBResources}"

    export AddTagsForALBResources="No"
    export AddTagsForAPIGatewayResources="No"
    export AddTagsForRDSResources="No"
    export AddTagsForEC2MetricsResources="No"
    export AddTagsForLambdaResources="No"
    export AddTagsForDynamoDBResources="No"

done
