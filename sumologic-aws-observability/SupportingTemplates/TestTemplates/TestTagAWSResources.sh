#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="tag_resource"
export AppName="tagresources"
export InstallTypes=("rds" "alb" "apigateway" "ec2" "lambda")

for InstallType in "${InstallTypes[@]}"
do
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
    AddTagsForLambdaResources="${AddTagsForLambdaResources}" AccountAlias="${AccountAlias}"

done

echo "All Installation Complete for ${AppName}"