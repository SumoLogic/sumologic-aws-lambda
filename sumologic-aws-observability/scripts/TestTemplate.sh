#!/bin/sh

export AWS_REGION="ap-south-1"
export AWS_PROFILE="personal"
# App to test
export AppName=master
export InstallType=onlyappswithexistingsources

# Sumo Logic Access Configuration
export Section1aSumoDeployment=""
export Section1bSumoAccessID=""
export Section1cSumoAccessKey=""
export Section1dSumoOrganizationId=""

cd ..\/

if [[ "${AppName}" != "master" ]]
then
    ./apps/${AppName}/test/TestTemplate.sh ${AWS_REGION} ${AWS_PROFILE} ${AppName} ${InstallType} ${Section1aSumoDeployment} \
    ${Section1bSumoAccessID} ${Section1cSumoAccessKey} ${Section1dSumoOrganizationId}
else
    ./templates/test/TestTemplate.sh ${AWS_REGION} ${AWS_PROFILE} ${AppName} ${InstallType} ${Section1aSumoDeployment} \
    ${Section1bSumoAccessID} ${Section1cSumoAccessKey} ${Section1dSumoOrganizationId}
fi