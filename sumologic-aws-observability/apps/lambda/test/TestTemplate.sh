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
export Section5eCloudTrailBucketPathExpression="*"
export Section5gCloudTrailLogsSourceCategoryName="Labs/${AppName}/${InstallType}"
export Section5bCloudTrailLogsBucketName="${AppName}-${InstallType}-${uid}"
export Section6dCloudWatchLogsSourceCategoryName="Labs/cloudwatch/${AppName}/${InstallType}"

export Section2aTagExistingAWSResources="No"
export Section3aInstallApp="No"
export Section4bCreateCloudWatchMetricsSource="No"
export Section5aCreateCloudTrailBucket="No"
export Section5dCreateCloudTrailLogSource="No"
export Section6bCreateCloudWatchLogSource="No"

if [[ "${InstallType}" == "all" ]]
then
    export Section4aCloudWatchMetricCollectorName="Sourabh-Collector-CW-${AppName}-${InstallType}"
    export Section5cCloudTrailCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section6aCloudWatchLogsCollectorName="Sourabh-Collector-logs-${AppName}-${InstallType}"
    export Section5fCloudTrailLogsSourceName="Source-${AppName}-${InstallType}"
    export Section6cCloudWatchLogsSourceName="cloudwatch-${AppName}-${InstallType}"
    export Section2aTagExistingAWSResources="Yes"
    export Section3aInstallApp="Yes"
    export Section4bCreateCloudWatchMetricsSource="Yes"
    export Section5aCreateCloudTrailBucket="Yes"
    export Section5dCreateCloudTrailLogSource="Yes"
    export Section6bCreateCloudWatchLogSource="Yes"
elif [[ "${InstallType}" == "onlyapp" ]]
then
    export Section3aInstallApp="Yes"
elif [[ "${InstallType}" == "onlytags" ]]
then
    export Section2aTagExistingAWSResources="Yes"
elif [[ "${InstallType}" == "onlycwsource" ]]
then
    export Section4aCloudWatchMetricCollectorName="Sourabh-Collector-CW-${AppName}-${InstallType}"
    export Section4bCreateCloudWatchMetricsSource="Yes"
elif [[ "${InstallType}" == "onlylogsourcewithbucket" ]]
then
    export Section5cCloudTrailCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section5fCloudTrailLogsSourceName="Source-${AppName}-${InstallType}"
    export Section5aCreateCloudTrailBucket="Yes"
    export Section5dCreateCloudTrailLogSource="Yes"
elif [[ "${InstallType}" == "onlylogsourcewithoutbucket" ]]
then
    export Section5cCloudTrailCollectorName="Sourabh-Collector-${AppName}-${InstallType}"
    export Section5fCloudTrailLogsSourceName="Source-${AppName}-${InstallType}"
    export Section5dCreateCloudTrailLogSource="Yes"
    export Section5bCloudTrailLogsBucketName="sumologiclambdahelper-${AWS_REGION}"
elif [[ "${InstallType}" == "onlycloudwatchlogsource" ]]
then
    export Section6aCloudWatchLogsCollectorName="Sourabh-Collector-logs-${AppName}-${InstallType}"
    export Section6cCloudWatchLogsSourceName="cloudwatch-${AppName}-${InstallType}"
    export Section6bCreateCloudWatchLogSource="Yes"
elif [[ "${InstallType}" == "updatesourceonly" ]]
then
    export Section5cCloudTrailCollectorName="Sourabh-Collector-${AppName}-onlylogsourcewithoutbucket"
    export Section5fCloudTrailLogsSourceName="Source-${AppName}-onlylogsourcewithoutbucket"
elif [[ "${InstallType}" == "updatecloudwatchsourceonly" ]]
then
    export Section6aCloudWatchLogsCollectorName="Sourabh-Collector-logs-${AppName}-onlycloudwatchlogsource"
    export Section6cCloudWatchLogsSourceName="cloudwatch-${AppName}-onlycloudwatchlogsource"
elif [[ "${InstallType}" == "nothing" ]]
then
    export Section6aCloudWatchLogsCollectorName=""
    export Section5cCloudTrailCollectorName=""
    export Section5fCloudTrailLogsSourceName=""
    export Section6cCloudWatchLogsSourceName=""
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"
pwd
aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./apps/${AppName}/lambda_app.template.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides Section1aSumoDeployment="${Section1aSumoDeployment}" Section1bSumoAccessID="${Section1bSumoAccessID}" \
Section1cSumoAccessKey="${Section1cSumoAccessKey}" Section1dSumoOrganizationId="${Section1dSumoOrganizationId}" \
Section1eRemoveSumoResourcesOnDeleteStack="${Section1eRemoveSumoResourcesOnDeleteStack}" Section2bAccountAlias="${Section2bAccountAlias}" \
Section2cFilterExpression="${Section2cFilterExpression}" Section4aCloudWatchMetricCollectorName="${Section4aCloudWatchMetricCollectorName}" \
Section4cCloudWatchMetricsSourceName="${Section4cCloudWatchMetricsSourceName}" Section5eCloudTrailBucketPathExpression="${Section5eCloudTrailBucketPathExpression}" \
Section5fCloudTrailLogsSourceName="${Section5fCloudTrailLogsSourceName}" Section5gCloudTrailLogsSourceCategoryName="${Section5gCloudTrailLogsSourceCategoryName}" \
Section2aTagExistingAWSResources="${Section2aTagExistingAWSResources}" Section3aInstallApp="${Section3aInstallApp}" \
Section4bCreateCloudWatchMetricsSource="${Section4bCreateCloudWatchMetricsSource}" Section5aCreateCloudTrailBucket="${Section5aCreateCloudTrailBucket}" \
Section5dCreateCloudTrailLogSource="${Section5dCreateCloudTrailLogSource}" Section5bCloudTrailLogsBucketName="${Section5bCloudTrailLogsBucketName}" \
Section6bCreateCloudWatchLogSource="${Section6bCreateCloudWatchLogSource}" Section6dCloudWatchLogsSourceCategoryName="${Section6dCloudWatchLogsSourceCategoryName}" \
Section6cCloudWatchLogsSourceName="${Section6cCloudWatchLogsSourceName}" Section6aCloudWatchLogsCollectorName="${Section6aCloudWatchLogsCollectorName}" \
Section5cCloudTrailCollectorName="${Section5cCloudTrailCollectorName}"
