#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="update_fields"
export AppName="updatefields"
export InstallTypes=("alb" "apigateway" "lambdacloudWatch")

for InstallType in "${InstallTypes[@]}"
do
    export CreateS3LogSource="Yes"
    export CreateDynamoDBCloudTrailLogSource="Yes"
    export CreateApiGatewayCloudTrailLogSource="Yes"
    export CreateLambdaCloudTrailLogSource="Yes"
    export CreateLambdaCloudWatchLogsSource="Yes"

    if [[ "${InstallType}" == "alb" ]]
    then
        export AlbS3LogsCollectorName="AWS-Sourabh-Collectoralb-all"
        export CreateS3LogSource="No"
        export AlbS3LogsSourceName="AWS-S3-alb-all-Source"
        export AccountAlias="albupdateaccount"
    elif [[ "${InstallType}" == "dynamo" ]]
    then
        export DynamoDBCloudTrailCollectorName="AWS-Sourabh-Collector-resources-all"
        export CreateDynamoDBCloudTrailLogSource="No"
        export DynamoDBCloudTrailLogsSourceName="AWS-CloudTrail-resources-all-Source"
        export AccountAlias="dynamoupdateaccount"
    elif [[ "${InstallType}" == "apigateway" ]]
    then
        export ApiGatewayCloudTrailCollectorName="AWS-Sourabh-Collector-resources-all"
        export CreateApiGatewayCloudTrailLogSource="No"
        export ApiGatewayCloudTrailLogsSourceName="AWS-CloudTrail-resources-all-Source"
        export AccountAlias="apigatewayupdateaccount"
    elif [[ "${InstallType}" == "lambdacloudtrail" ]]
    then
        export LambdaCloudTrailCollectorName="AWS-Sourabh-Collector-resources-all"
        export CreateLambdaCloudTrailLogSource="No"
        export LambdaCloudTrailLogsSourceName="AWS-CloudTrail-resources-all-Source"
        export AccountAlias="lambdaupdateaccount"
    elif [[ "${InstallType}" == "lambdacloudWatch" ]]
    then
        export LambdaCloudWatchLogsCollectorName="AWS-Sourabh-Collector-resources-all"
        export CreateLambdaCloudWatchLogsSource="No"
        export LambdaCloudWatchLogsSourceName="AWS-CloudWatch-Logs-resources-all-Source"
        export AccountAlias="lambdacloudwatch"
    else
        echo "No Choice"
    fi

    # Export Sumo Properties
    export SumoAccessID=""
    export SumoAccessKey=""
    export SumoDeployment="us1"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    AlbS3LogsCollectorName="${AlbS3LogsCollectorName}" CreateS3LogSource="${CreateS3LogSource}" AlbS3LogsSourceName="${AlbS3LogsSourceName}" \
    AccountAlias="${AccountAlias}" DynamoDBCloudTrailCollectorName="${DynamoDBCloudTrailCollectorName}" CreateDynamoDBCloudTrailLogSource="${CreateDynamoDBCloudTrailLogSource}" \
    DynamoDBCloudTrailLogsSourceName="${DynamoDBCloudTrailLogsSourceName}" ApiGatewayCloudTrailCollectorName="${ApiGatewayCloudTrailCollectorName}" \
    CreateApiGatewayCloudTrailLogSource="${CreateApiGatewayCloudTrailLogSource}" ApiGatewayCloudTrailLogsSourceName="${ApiGatewayCloudTrailLogsSourceName}" \
    LambdaCloudTrailCollectorName="${LambdaCloudTrailCollectorName}" CreateLambdaCloudTrailLogSource="${CreateLambdaCloudTrailLogSource}" \
    LambdaCloudTrailLogsSourceName="${LambdaCloudTrailLogsSourceName}" LambdaCloudWatchLogsCollectorName="${LambdaCloudWatchLogsCollectorName}" \
    CreateLambdaCloudWatchLogsSource="${CreateLambdaCloudWatchLogsSource}" LambdaCloudWatchLogsSourceName="${LambdaCloudWatchLogsSourceName}"

done

echo "All Installation Complete for ${AppName}"