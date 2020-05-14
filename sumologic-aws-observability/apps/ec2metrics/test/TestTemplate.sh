#!/bin/sh

export AWS_REGION=$1
export AWS_PROFILE=$2
# App to test
export AppName=$3
export InstallType=$4

# Sumo Logic Access Configuration
export Section1aSumoDeployment=$5
export Section1bSumoAccessID=$6
export Section1cSumoAccessKey=$7
export Section1dSumoOrganizationId=$8
export Section1eRemoveSumoResourcesOnDeleteStack=true

export Section2bAccountAlias=${InstallType}
export Section2cFilterExpression=".*"
export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
export Section4bMetaDataSourceName="Source-${AppName}-${InstallType}"

if [[ "${InstallType}" == "all" ]]
then
    export Section2aTagExistingAWSResources="Yes"
    export Section3aInstallApp="Yes"
    export Section4aCreateMetaDataSource="Yes"
elif [[ "${InstallType}" == "onlyapp" ]]
then
    export Section2aTagExistingAWSResources="No"
    export Section3aInstallApp="Yes"
    export Section4aCreateMetaDataSource="No"
elif [[ "${InstallType}" == "onlytags" ]]
then
    export Section2aTagExistingAWSResources="Yes"
    export Section3aInstallApp="No"
    export Section4aCreateMetaDataSource="No"
elif [[ "${InstallType}" == "onlysource" ]]
then
    export Section2aTagExistingAWSResources="No"
    export Section3aInstallApp="No"
    export Section4aCreateMetaDataSource="Yes"
elif [[ "${InstallType}" == "nothing" ]]
then
    export Section2aTagExistingAWSResources="No"
    export Section3aInstallApp="No"
    export Section4aCreateMetaDataSource="No"
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"
pwd
aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./apps/${AppName}/ec2_metrics_app.template.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides Section1aSumoDeployment="${Section1aSumoDeployment}" Section1bSumoAccessID="${Section1bSumoAccessID}" \
Section1cSumoAccessKey="${Section1cSumoAccessKey}" Section1dSumoOrganizationId="${Section1dSumoOrganizationId}" \
Section1eRemoveSumoResourcesOnDeleteStack="${Section1eRemoveSumoResourcesOnDeleteStack}" Section2bAccountAlias="${Section2bAccountAlias}" \
Section2cFilterExpression="${Section2cFilterExpression}" Section3bCollectorName="${Section3bCollectorName}" \
Section4bMetaDataSourceName="${Section4bMetaDataSourceName}" Section2aTagExistingAWSResources="${Section2aTagExistingAWSResources}" \
Section3aInstallApp="${Section3aInstallApp}" Section4aCreateMetaDataSource="${Section4aCreateMetaDataSource}"



