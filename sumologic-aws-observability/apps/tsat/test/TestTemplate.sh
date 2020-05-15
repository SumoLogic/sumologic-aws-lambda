#!/bin/sh

export AWS_REGION=$1
export AWS_PROFILE=$2
# App to test
export AppName=$3
export InstallType=$4

export uid=`cat /dev/random | LC_CTYPE=C tr -dc "[:lower:]" | head -c 6`

# Sumo Logic Access Configuration
export Section1aSumoDeployment=$5
export Section1bSumoAccessID=$6
export Section1cSumoAccessKey=$7
export Section1dSumoOrganizationId=$8
export Section1eRemoveSumoResourcesOnDeleteStack=true

export Section3cNamespaces="AWS/ApplicationELB, AWS/ApiGateway, AWS/DynamoDB, AWS/Lambda, AWS/RDS"

export Section2aInstallApp="No"
export Section3aCreateAwsInventorySource="No"

if [[ "${InstallType}" == "all" ]]
then
    export Section2bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section3bAwsInventorySourceName="Source-${AppName}-${InstallType}"
    export Section3aCreateAwsInventorySource="Yes"
    export Section2aInstallApp="Yes"
elif [[ "${InstallType}" == "onlyapp" ]]
then
    export Section2aInstallApp="Yes"
elif [[ "${InstallType}" == "onlysource" ]]
then
    export Section2bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section3bAwsInventorySourceName="Source-${AppName}-${InstallType}"
    export Section3aCreateAwsInventorySource="Yes"
elif [[ "${InstallType}" == "nothing" ]]
then
    export Section2bCollectorName=""
    export Section3bAwsInventorySourceName=""
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"
pwd
aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./apps/${AppName}/tsat.template.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides Section1aSumoDeployment="${Section1aSumoDeployment}" Section1bSumoAccessID="${Section1bSumoAccessID}" \
Section1cSumoAccessKey="${Section1cSumoAccessKey}" Section1dSumoOrganizationId="${Section1dSumoOrganizationId}" \
Section1eRemoveSumoResourcesOnDeleteStack="${Section1eRemoveSumoResourcesOnDeleteStack}" Section3cNamespaces="${Section3cNamespaces}" \
Section2aInstallApp="${Section2aInstallApp}" Section3aCreateAwsInventorySource="${Section3aCreateAwsInventorySource}" \
Section2bCollectorName="${Section2bCollectorName}" Section3bAwsInventorySourceName="${Section3bAwsInventorySourceName}"


