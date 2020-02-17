#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="tag_resources"
export AppName="tag"
export InstallTypes=("all")

for InstallType in "${InstallTypes[@]}"
do
    export AccountAlias="testrds${InstallType}"
    export AddTagsForALBResources="Yes"
    export AddTagsForAPIGatewayResources="No"
    export AddTagsForRDSResources="No"
    export AddTagsForEC2MetricsResources="No"
    export AddTagsForLambdaResources="No"
    export AddTagsForDynamoDBResources="No"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../sam/${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides AddTagsForALBResources="${AddTagsForALBResources}" AddTagsForAPIGatewayResources="${AddTagsForAPIGatewayResources}" \
    AddTagsForRDSResources="${AddTagsForRDSResources}" AddTagsForEC2MetricsResources="${AddTagsForEC2MetricsResources}" \
    AddTagsForLambdaResources="${AddTagsForLambdaResources}" AccountAlias="${AccountAlias}" AddTagsForDynamoDBResources="${AddTagsForDynamoDBResources}"

done

echo "All Installation Complete for ${AppName}"