#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="lambda_app"
export AppName="lambda"
export InstallTypes=("all" "onlyapp" "appcloudtrail" "appcloudtrails3bucket" "appcloudwatch" "appcloudwatchmetrics")

for InstallType in "${InstallTypes[@]}"
do
    export CloudTrailLogsBucketName="${AppName}-${InstallType}-qwerty"
    export AccountAlias="testlambda${InstallType}"

    if [[ "${InstallType}" == "all" ]]
    then
        export CreateCloudTrailBucket="Yes"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchLogSource="Yes"
        export CreateCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "onlyapp" ]]
    then
        export CreateCloudTrailBucket="No"
        export CreateCloudTrailLogSource="No"
        export CreateCloudWatchLogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudtrail" ]]
    then
        export CreateCloudTrailBucket="No"
        export CloudTrailLogsBucketName="lambda-all-randmomstring"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchLogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudtrails3bucket" ]]
    then
        export CreateCloudTrailBucket="Yes"
        export CreateCloudTrailLogSource="Yes"
        export CreateCloudWatchLogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudwatch" ]]
    then
        export CreateCloudTrailBucket="No"
        export CreateCloudTrailLogSource="No"
        export CreateCloudWatchLogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudwatchmetrics" ]]
    then
        export CreateCloudTrailBucket="No"
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

    # Export Collector Name
    export CollectorName="AWS-Sourabh-Collector${AppName}-${InstallType}"

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

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../sam/${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    CollectorName="${CollectorName}" CloudTrailLogsBucketName="${CloudTrailLogsBucketName}" CloudTrailBucketPathExpression="${CloudTrailBucketPathExpression}" \
    CloudTrailLogsSourceName="${CloudTrailLogsSourceName}" CloudTrailLogsSourceCategoryName="${CloudTrailLogsSourceCategoryName}" \
    CloudWatchLogsSourceName="${CloudWatchLogsSourceName}" CloudWatchLogsSourceCategoryName="${CloudWatchLogsSourceCategoryName}" \
    AccountAlias="${AccountAlias}" CloudWatchMetricsSourceName="${CloudWatchMetricsSourceName}" CloudWatchMetricsSourceCategoryName="${CloudWatchMetricsSourceCategoryName}" \
    CreateCloudTrailBucket="${CreateCloudTrailBucket}" CreateCloudTrailLogSource="${CreateCloudTrailLogSource}" CreateCloudWatchLogSource="${CreateCloudWatchLogSource}" \
    CreateCloudWatchMetricsSource="${CreateCloudWatchMetricsSource}"

done

echo "All Installation Complete for ${AppName}"
