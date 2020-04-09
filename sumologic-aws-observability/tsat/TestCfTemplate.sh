#!/bin/sh

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppName=tsat
export InstallType=all

# Sumo Logic Access Configuration
export SumoAccessID=""
export SumoAccessKey=""
export SumoOrganizationId=""
export SumoDeployment="nite"
export RemoveSumoResourcesOnDeleteStack=true

# App Details - Collector Configuration
export CollectorName="AWS-Sourabh-Collector-${AppName}-${InstallType}"
export AwsInventorySourceName="AWS-source-${AppName}-${InstallType}"
export AwsInventorySourceCategoryName="Aws/Source/${AppName}/${InstallType}"
export Namespaces="AWS/ApplicationELB, AWS/ApiGateway, AWS/DynamoDB, AWS/Lambda, AWS/RDS"

if [[ "${InstallType}" == "all" ]]
then
    export CreateCollector="Yes"
    export CreateAwsInventorySource="Yes"
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"

aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./tsat.template.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" SumoOrganizationId="${SumoOrganizationId}" \
CreateCollector="${CreateCollector}" CollectorName="${CollectorName}" CreateAwsInventorySource="${CreateAwsInventorySource}" \
AwsInventorySourceName="${AwsInventorySourceName}" AwsInventorySourceCategoryName="${AwsInventorySourceCategoryName}" \
Namespaces="${Namespaces}"
