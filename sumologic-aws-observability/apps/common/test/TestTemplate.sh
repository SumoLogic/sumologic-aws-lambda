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

export Section2aAccountAlias=${InstallType}
export Section4bCloudWatchMetricsSourceName="Source-metrics-${AppName}-${InstallType}"
export Section5bCommonBucketName="${AppName}-${InstallType}-${uid}"

export Section3aCreateCollector="No"
export Section4aCreateCloudWatchMetricsSource="No"
export Section5aCreateCommonBucket="No"
export Section5cCreateTrail="No"

if [[ "${InstallType}" == "all" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section3aCreateCollector="Yes"
    export Section4aCreateCloudWatchMetricsSource="Yes"
    export Section5aCreateCommonBucket="Yes"
    export Section5cCreateTrail="Yes"
elif [[ "${InstallType}" == "onlycollector" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section3aCreateCollector="Yes"
elif [[ "${InstallType}" == "onlycwsource" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section4aCreateCloudWatchMetricsSource="Yes"
    export Section3aCreateCollector="Yes"
elif [[ "${InstallType}" == "onlybukcetwithtrail" ]]
then
    export Section5cCreateTrail="Yes"
    export Section5aCreateCommonBucket="Yes"
elif [[ "${InstallType}" == "onlybukcetwithouttrail" ]]
then
    export Section5aCreateCommonBucket="Yes"
elif [[ "${InstallType}" == "nothing" ]]
then
    export Section3bCollectorName=""
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"
pwd
aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./apps/${AppName}/resources.template.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides Section1aSumoDeployment="${Section1aSumoDeployment}" Section1bSumoAccessID="${Section1bSumoAccessID}" \
Section1cSumoAccessKey="${Section1cSumoAccessKey}" Section1dSumoOrganizationId="${Section1dSumoOrganizationId}" \
Section1eRemoveSumoResourcesOnDeleteStack="${Section1eRemoveSumoResourcesOnDeleteStack}" Section2aAccountAlias="${Section2aAccountAlias}" \
Section3bCollectorName="${Section3bCollectorName}" Section5cCreateTrail="${Section5cCreateTrail}" \
Section4bCloudWatchMetricsSourceName="${Section4bCloudWatchMetricsSourceName}" Section3aCreateCollector="${Section3aCreateCollector}" \
Section4aCreateCloudWatchMetricsSource="${Section4aCreateCloudWatchMetricsSource}" Section5aCreateCommonBucket="${Section5aCreateCommonBucket}" \
Section5bCommonBucketName="${Section5bCommonBucketName}"
