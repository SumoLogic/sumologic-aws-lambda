#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="alb_app"
export AppName="alb"
export InstallTypes=("all" "onlyapp" "apps3source" "apps3sources3bucket" "appcloudwatchmetrics")

for InstallType in "${InstallTypes[@]}"
do
    export S3LogsBucketName="${AppName}-${InstallType}-qwerty"
    export AccountAlias="testalb${InstallType}"

    if [[ "${InstallType}" == "all" ]]
    then
        export CreateS3Bucket="Yes"
        export CreateS3LogSource="Yes"
        export CreateCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "onlyapp" ]]
    then
        export CreateS3Bucket="No"
        export CreateS3LogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "apps3source" ]]
    then
        export CreateS3Bucket="No"
        export S3LogsBucketName="lambda-all-randmomstring"
        export CreateS3LogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "apps3sources3bucket" ]]
    then
        export CreateS3Bucket="Yes"
        export CreateS3LogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudwatchmetrics" ]]
    then
        export CreateS3Bucket="No"
        export CreateS3LogSource="No"
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

    # Export S3 Logs Details
    export S3BucketPathExpression="*"
    export S3LogsSourceName="AWS-S3-${AppName}-${InstallType}-Source"
    export S3LogsSourceCategoryName="AWS/S3/${AppName}/${InstallType}/Logs"

    # Export CloudWatch Metrics Details
    export AWSRegion="Current Region"
    export CloudWatchMetricsSourceName="AWS-CloudWatch-Metrics-${AppName}-${InstallType}-Source"
    export CloudWatchMetricsSourceCategoryName="AWS/CloudWatch/${AppName}/${InstallType}/Metrics"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    CollectorName="${CollectorName}" S3LogsBucketName="${S3LogsBucketName}" S3BucketPathExpression="${S3BucketPathExpression}" \
    S3LogsSourceName="${S3LogsSourceName}" S3LogsSourceCategoryName="${S3LogsSourceCategoryName}" \
    AWSRegion="${AWSRegion}" CloudWatchMetricsSourceName="${CloudWatchMetricsSourceName}" CloudWatchMetricsSourceCategoryName="${CloudWatchMetricsSourceCategoryName}" \
    CreateS3Bucket="${CreateS3Bucket}" CreateS3LogSource="${CreateS3LogSource}" CreateCloudWatchMetricsSource="${CreateCloudWatchMetricsSource}" AccountAlias="${AccountAlias}"

done

echo "All Installation Complete for ${AppName}"