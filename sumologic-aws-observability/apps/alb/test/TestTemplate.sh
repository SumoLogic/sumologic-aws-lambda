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
export Section4cCloudWatchMetricsSourceName="Source-metrics-${AppName}-${InstallType}"
export Section5eS3BucketPathExpression="*"
export Section5gALBLogsSourceCategoryName="Labs/${AppName}/${InstallType}"
export Section5bS3LogsBucketName="${AppName}-${InstallType}-${uid}"

export Section2aTagExistingAWSResources="No"
export Section3aInstallApp="No"
export Section4bCreateCloudWatchMetricsSource="No"
export Section5aCreateS3Bucket="No"
export Section5dCreateALBLogSource="No"

if [[ "${InstallType}" == "all" ]]
then
    export Section4aCloudWatchMetricCollectorName="sourabh-collector-CW-${AppName}-${InstallType}"
    export Section5cALBCollectorName="sourabh-Collector-${AppName}-${InstallType}"
    export Section5fALBLogsSourceName="Source-${AppName}-${InstallType}"
    export Section2aTagExistingAWSResources="Yes"
    export Section3aInstallApp="Yes"
    export Section4bCreateCloudWatchMetricsSource="Yes"
    export Section5aCreateS3Bucket="Yes"
    export Section5dCreateALBLogSource="Yes"
elif [[ "${InstallType}" == "onlyapp" ]]
then
    export Section3aInstallApp="Yes"
elif [[ "${InstallType}" == "onlytags" ]]
then
    export Section2aTagExistingAWSResources="Yes"
elif [[ "${InstallType}" == "onlycwsource" ]]
then
    export Section4aCloudWatchMetricCollectorName="sourabh-Collector-CW-${AppName}-${InstallType}"
    export Section4bCreateCloudWatchMetricsSource="Yes"
elif [[ "${InstallType}" == "onlylogsourcewithbucket" ]]
then
    export Section5cALBCollectorName="sourabh-Collector-${AppName}-${InstallType}"
    export Section5fALBLogsSourceName="Source-${AppName}-${InstallType}"
    export Section5aCreateS3Bucket="Yes"
    export Section5dCreateALBLogSource="Yes"
elif [[ "${InstallType}" == "onlylogsourcewithoutbucket" ]]
then
    export Section5cALBCollectorName="sourabh-Collector-${AppName}-${InstallType}"
    export Section5fALBLogsSourceName="Source-${AppName}-${InstallType}"
    export Section5dCreateALBLogSource="Yes"
    export Section5bS3LogsBucketName="sumologiclambdahelper-${AWS_REGION}"
elif [[ "${InstallType}" == "updatesourceonly" ]]
then
    export Section5cALBCollectorName="sourabh-Collector-${AppName}-onlylogsourcewithoutbucket"
    export Section5fALBLogsSourceName="Source-${AppName}-onlylogsourcewithoutbucket"
elif [[ "${InstallType}" == "nothing" ]]
then
    export Section5cALBCollectorName=""
    export Section5fALBLogsSourceName=""
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"
pwd
aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./apps/${AppName}/alb_app.template.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides Section1aSumoDeployment="${Section1aSumoDeployment}" Section1bSumoAccessID="${Section1bSumoAccessID}" \
Section1cSumoAccessKey="${Section1cSumoAccessKey}" Section1dSumoOrganizationId="${Section1dSumoOrganizationId}" \
Section1eRemoveSumoResourcesOnDeleteStack="${Section1eRemoveSumoResourcesOnDeleteStack}" Section2bAccountAlias="${Section2bAccountAlias}" \
Section2cFilterExpression="${Section2cFilterExpression}" Section5cALBCollectorName="${Section5cALBCollectorName}" \
Section4cCloudWatchMetricsSourceName="${Section4cCloudWatchMetricsSourceName}" Section5eS3BucketPathExpression="${Section5eS3BucketPathExpression}" \
Section5fALBLogsSourceName="${Section5fALBLogsSourceName}" Section5gALBLogsSourceCategoryName="${Section5gALBLogsSourceCategoryName}" \
Section2aTagExistingAWSResources="${Section2aTagExistingAWSResources}" Section3aInstallApp="${Section3aInstallApp}" \
Section4bCreateCloudWatchMetricsSource="${Section4bCreateCloudWatchMetricsSource}" Section5aCreateS3Bucket="${Section5aCreateS3Bucket}" \
Section5dCreateALBLogSource="${Section5dCreateALBLogSource}" Section5bS3LogsBucketName="${Section5bS3LogsBucketName}" \
Section4aCloudWatchMetricCollectorName="${Section4aCloudWatchMetricCollectorName}"


