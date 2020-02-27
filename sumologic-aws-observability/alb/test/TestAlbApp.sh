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
    export InstallApp="Yes"

    if [[ "${InstallType}" == "all" ]]
    then
        export CreateS3Bucket="Yes"
        export CreateELBLogSource="Yes"
        export CreateCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "onlyapp" ]]
    then
        export CreateS3Bucket="No"
        export CreateELBLogSource="No"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "apps3source" ]]
    then
        export CreateS3Bucket="No"
        export S3LogsBucketName="lambda-all-randmomstring"
        export CreateELBLogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "apps3sources3bucket" ]]
    then
        export CreateS3Bucket="Yes"
        export CreateELBLogSource="Yes"
        export CreateCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "appcloudwatchmetrics" ]]
    then
        export CreateS3Bucket="No"
        export CreateELBLogSource="No"
        export CreateCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "noapp" ]]
    then
        export CreateS3Bucket="Yes"
        export CreateELBLogSource="Yes"
        export CreateCloudWatchMetricsSource="Yes"
        export InstallApp="No"
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
    export ELBLogsSourceName="AWS-S3-${AppName}-${InstallType}-Source"
    export ELBLogsSourceCategoryName="AWS/S3/${AppName}/${InstallType}/Logs"

    # Export CloudWatch Metrics Details
    export CloudWatchMetricsSourceName="AWS-CloudWatch-Metrics-${AppName}-${InstallType}-Source"
    export CloudWatchMetricsSourceCategoryName="AWS/CloudWatch/${AppName}/${InstallType}/Metrics"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../sam/${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    CollectorName="${CollectorName}" S3LogsBucketName="${S3LogsBucketName}" S3BucketPathExpression="${S3BucketPathExpression}" \
    ELBLogsSourceName="${ELBLogsSourceName}" ELBLogsSourceCategoryName="${ELBLogsSourceCategoryName}" InstallApp="${InstallApp}"\
    CloudWatchMetricsSourceName="${CloudWatchMetricsSourceName}" CloudWatchMetricsSourceCategoryName="${CloudWatchMetricsSourceCategoryName}" \
    CreateS3Bucket="${CreateS3Bucket}" CreateELBLogSource="${CreateELBLogSource}" CreateCloudWatchMetricsSource="${CreateCloudWatchMetricsSource}" AccountAlias="${AccountAlias}"

done

echo "All Installation Complete for ${AppName}"