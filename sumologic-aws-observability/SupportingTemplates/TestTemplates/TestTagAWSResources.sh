#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="tag_resource"
export AppName="tagresources"
export InstallTypes=("all" "rds" "alb" "apigateway" "ec2" "lambda")

for InstallType in "${InstallTypes[@]}"
do
    export AddTagsForDynamoDBResources="No"

    if [[ "${InstallType}" == "rds" ]]
    then
        export AddTagsForALBResources="No"
        export AddTagsForAPIGatewayResources="No"
        export AddTagsForRDSResources="Yes"
        export AddTagsForEC2MetricsResources="No"
        export AddTagsForLambdaResources="No"
    elif [[ "${InstallType}" == "alb" ]]
    then
        export AddTagsForALBResources="Yes"
        export AddTagsForAPIGatewayResources="No"
        export AddTagsForRDSResources="No"
        export AddTagsForEC2MetricsResources="No"
        export AddTagsForLambdaResources="No"
    elif [[ "${InstallType}" == "apigateway" ]]
    then
        export AddTagsForALBResources="No"
        export AddTagsForAPIGatewayResources="Yes"
        export AddTagsForRDSResources="No"
        export AddTagsForEC2MetricsResources="No"
        export AddTagsForLambdaResources="No"
    elif [[ "${InstallType}" == "ec2" ]]
    then
        export AddTagsForALBResources="No"
        export AddTagsForAPIGatewayResources="No"
        export AddTagsForRDSResources="No"
        export AddTagsForEC2MetricsResources="Yes"
        export AddTagsForLambdaResources="No"
    elif [[ "${InstallType}" == "lambda" ]]
    then
        export AddTagsForALBResources="No"
        export AddTagsForAPIGatewayResources="No"
        export AddTagsForRDSResources="No"
        export AddTagsForEC2MetricsResources="No"
        export AddTagsForLambdaResources="Yes"
    elif [[ "${InstallType}" == "dynamodb" ]]
    then
        export AddTagsForALBResources="No"
        export AddTagsForAPIGatewayResources="No"
        export AddTagsForRDSResources="No"
        export AddTagsForEC2MetricsResources="No"
        export AddTagsForLambdaResources="No"
        export AddTagsForDynamoDBResources="Yes"
    elif [[ "${InstallType}" == "all" ]]
    then
        export AddTagsForALBResources="Yes"
        export AddTagsForAPIGatewayResources="Yes"
        export AddTagsForRDSResources="Yes"
        export AddTagsForEC2MetricsResources="Yes"
        export AddTagsForLambdaResources="Yes"
        export AddTagsForDynamoDBResources="Yes"
    else
        echo "No Choice"
    fi

    # Export Sumo Properties
    export SumoAccessID=""
    export SumoAccessKey=""
    export SumoOrganizationId=""
    export SumoDeployment="us1"
    export RemoveSumoResourcesOnDeleteStack=true

    # Export Tags Details
    export AccountAlias="testing-tags"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    AddTagsForALBResources="${AddTagsForALBResources}" AddTagsForAPIGatewayResources="${AddTagsForAPIGatewayResources}" \
    AddTagsForRDSResources="${AddTagsForRDSResources}" AddTagsForEC2MetricsResources="${AddTagsForEC2MetricsResources}" \
    AddTagsForLambdaResources="${AddTagsForLambdaResources}" AccountAlias="${AccountAlias}" AddTagsForDynamoDBResources="${AddTagsForDynamoDBResources}"

done

echo "All Installation Complete for ${AppName}"