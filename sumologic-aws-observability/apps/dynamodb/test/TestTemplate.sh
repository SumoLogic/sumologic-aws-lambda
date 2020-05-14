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

export Section2bAccountAlias=${InstallType}
export Section2cFilterExpression=".*"
export Section4bCloudWatchMetricsSourceName="Source-metrics-${AppName}-${InstallType}"
export Section5dCloudTrailBucketPathExpression="DYNAMODB_LOGS"
export Section5fCloudTrailLogsSourceCategoryName="Labs/${AppName}/${InstallType}"
export Section5bCloudTrailLogsBucketName="${AppName}-${InstallType}-${uid}"

export Section2aTagExistingAWSResources="No"
export Section3aInstallApp="No"
export Section4aCreateCloudWatchMetricsSource="No"
export Section5aCreateCloudTrailBucket="No"
export Section5cCreateCloudTrailLogSource="No"

if [[ "${InstallType}" == "all" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section5eCloudTrailLogsSourceName="Source-${AppName}-${InstallType}"
    export Section2aTagExistingAWSResources="Yes"
    export Section3aInstallApp="Yes"
    export Section4aCreateCloudWatchMetricsSource="Yes"
    export Section5aCreateCloudTrailBucket="Yes"
    export Section5cCreateCloudTrailLogSource="Yes"
elif [[ "${InstallType}" == "onlyapp" ]]
then
    export Section3aInstallApp="Yes"
elif [[ "${InstallType}" == "onlytags" ]]
then
    export Section2aTagExistingAWSResources="Yes"
elif [[ "${InstallType}" == "onlycwsource" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section4aCreateCloudWatchMetricsSource="Yes"
elif [[ "${InstallType}" == "onlylogsourcewithbucket" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section5eCloudTrailLogsSourceName="Source-${AppName}-${InstallType}"
    export Section5aCreateCloudTrailBucket="Yes"
    export Section5cCreateCloudTrailLogSource="Yes"
elif [[ "${InstallType}" == "onlylogsourcewithoutbucket" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section5eCloudTrailLogsSourceName="Source-${AppName}-${InstallType}"
    export Section5cCreateCloudTrailLogSource="Yes"
    export Section5bCloudTrailLogsBucketName="sumologiclambdahelper-${AWS_REGION}"
elif [[ "${InstallType}" == "updatesourceonly" ]]
then
    export Section3bCollectorName="Sourabh-Collector-${AppName}-onlylogsourcewithoutbucket"
    export Section5eCloudTrailLogsSourceName="Source-${AppName}-onlylogsourcewithoutbucket"
elif [[ "${InstallType}" == "nothing" ]]
then
    export Section3bCollectorName=""
    export Section5eCloudTrailLogsSourceName=""
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"
pwd
aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./apps/${AppName}/dynamodb_app.template.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides Section1aSumoDeployment="${Section1aSumoDeployment}" Section1bSumoAccessID="${Section1bSumoAccessID}" \
Section1cSumoAccessKey="${Section1cSumoAccessKey}" Section1dSumoOrganizationId="${Section1dSumoOrganizationId}" \
Section1eRemoveSumoResourcesOnDeleteStack="${Section1eRemoveSumoResourcesOnDeleteStack}" Section2bAccountAlias="${Section2bAccountAlias}" \
Section2cFilterExpression="${Section2cFilterExpression}" Section3bCollectorName="${Section3bCollectorName}" \
Section4bCloudWatchMetricsSourceName="${Section4bCloudWatchMetricsSourceName}" Section5dCloudTrailBucketPathExpression="${Section5dCloudTrailBucketPathExpression}" \
Section5eCloudTrailLogsSourceName="${Section5eCloudTrailLogsSourceName}" Section5fCloudTrailLogsSourceCategoryName="${Section5fCloudTrailLogsSourceCategoryName}" \
Section2aTagExistingAWSResources="${Section2aTagExistingAWSResources}" Section3aInstallApp="${Section3aInstallApp}" \
Section4aCreateCloudWatchMetricsSource="${Section4aCreateCloudWatchMetricsSource}" Section5aCreateCloudTrailBucket="${Section5aCreateCloudTrailBucket}" \
Section5cCreateCloudTrailLogSource="${Section5cCreateCloudTrailLogSource}" Section5bCloudTrailLogsBucketName="${Section5bCloudTrailLogsBucketName}"
