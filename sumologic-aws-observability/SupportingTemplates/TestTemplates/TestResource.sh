#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="resources"
export AppName="resources"
export InstallTypes=("cloudtrails3bucket" "cloudtrail" "cloudwatchlogs" "cloudwatchmetrics")

for InstallType in "${InstallTypes[@]}"
do
    export BucketName="${AppName}-${InstallType}-qwerty"
    export AccountAlias="testresources${InstallType}"

    if [[ "${InstallType}" == "all" ]]
    then
        export CreateS3Bucket="Yes"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchLogSource="Yes"
        export CreateCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "cloudtrails3bucket" ]]
    then
        export CreateS3Bucket="Yes"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchLogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "cloudtrail" ]]
    then
        export BucketName="lambda-all-randmomstring"
        export CreateS3Bucket="No"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchLogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "cloudwatchlogs" ]]
    then
        export CreateS3Bucket="No"
        export CreateCloudTrailLogSource="No"
        export CreateCloudWatchLogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "cloudwatchmetrics" ]]
    then
        export CreateS3Bucket="No"
        export CreateCloudTrailLogSource="No"
        export CreateCloudWatchLogSource="No"
        export CreateCloudWatchMetricsSource="Yes"
    else
        echo "No Choice"
    fi

    # Export Sumo Properties
    export SumoAccessID=""
    export SumoAccessKey=""
    export SumoOrganizationId=""
    export SumoDeployment="us1"
    export RemoveSumoResourcesOnDeleteStack=true
    export AWSRegion="Current Region"

    # Export Collector Name
    export CollectorName="AWS-Sourabh-Collector-${AppName}-${InstallType}"

    # Export CloudTrail Logs Details
    export CloudTrailBucketPathExpression="*"
    export CloudTrailLogsSourceName="AWS-CloudTrail-${AppName}-${InstallType}-Source"
    export CloudTrailLogsSourceCategoryName="AWS/CloudTrail/${AppName}/${InstallType}/Logs"

    # Export CloudWatch Logs Details
    export CloudWatchLogsSourceName="AWS-CloudWatch-Logs-${AppName}-${InstallType}-Source"
    export CloudWatchLogsSourceCategoryName="AWS/CloudWatch/${AppName}/${InstallType}/Logs"

    # Export CloudWatch Metrics Details
    export CloudWatchMetricsSourceName="AWS-CloudWatch-Metrics-${AppName}-${InstallType}-Source"
    export CloudWatchMetricsSourceCategoryName="AWS/CloudWatch/${AppName}/${InstallType}/Metrics"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    CollectorName="${CollectorName}" BucketName="${BucketName}" CloudTrailBucketPathExpression="${CloudTrailBucketPathExpression}" \
    CloudTrailLogsSourceName="${CloudTrailLogsSourceName}" CloudTrailLogsSourceCategoryName="${CloudTrailLogsSourceCategoryName}" \
    CloudWatchLogsSourceName="${CloudWatchLogsSourceName}" CloudWatchLogsSourceCategoryName="${CloudWatchLogsSourceCategoryName}" \
    AWSRegion="${AWSRegion}" CloudWatchMetricsSourceName="${CloudWatchMetricsSourceName}" CloudWatchMetricsSourceCategoryName="${CloudWatchMetricsSourceCategoryName}" \
    CreateS3Bucket="${CreateS3Bucket}" CreateCloudTrailLogSource="${CreateCloudTrailLogSource}" CreateCloudWatchLogSource="${CreateCloudWatchLogSource}" \
    CreateCloudWatchMetricsSource="${CreateCloudWatchMetricsSource}" AccountAlias="${AccountAlias}"

done

echo "All Installation Complete for ${AppName}"