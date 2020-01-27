#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="sumologic_observability.master"
export AppName="master"

# export InstallTypes=("nothing" "explorer")
# export InstallTypes=("ec2app" "ec2withMeta")
# export InstallTypes=("alldynamo" "dynamoapp" "dynamoallwithexistingbucket" "albapp")
# export InstallTypes=("allalb")
# export InstallTypes=("alballwithexistingbucket")
# export InstallTypes=("rdsapp" "rdscloudwatch" "allapi" "apiapp" "apiallwithexistingbucket")
# export InstallTypes=("lambdall" "lambdaapp" "lambdappwithexistingbucket")
# export InstallTypes=("lambdacloud")
# export InstallTypes=("allinstalls")
export InstallTypes=("tagmetricrulesandApps")

for InstallType in "${InstallTypes[@]}"
do

    export AccountAlias="test-master-${InstallType}"

    # Export Explorer Option
    export ExplorerName="AWS Explorer Test View"
    export CreateExplorerView="No"

    # EC2 App Configuration
    export InstallEC2App="No"
    export CreateMetaDataSource="No"
    export Ec2AppSourceCategoryName="HostMetrics"

    # ALB App Configuration
    export InstallALBApp="No"
    export CreateS3Bucket="No"
    export S3LogsBucketName="lambda-all-randmomstring"
    export CreateS3LogSource="No"
    export AlbS3LogsCollectorName="alb-my-collector"
    export AlbS3LogsSourceName="alb-my-source"
    export AlbS3LogsSourceCategoryName="ALB/Existing/Logs"
    export CreateAlbCloudWatchMetricsSource="No"
    export AlbCloudWatchMetricsSourceCategoryName="ALB/Existing/Metrics"

    # Dynamo DB App Configuration
    export InstallDynamoDBApp="No"
    export CreateDynamoDBCloudTrailBucket="No"
    export DynamoDBCloudTrailLogsBucketName="lambda-all-randmomstring"
    export CreateDynamoDBCloudTrailLogSource="No"
    export DynamoDBCloudTrailCollectorName="dynamo-my-collector"
    export DynamoDBCloudTrailLogsSourceName="dynamo-my-source"
    export DynamoDBCloudTrailLogsSourceCategoryName="Dynamo/Existing/Logs"
    export CreateDynamoDBCloudWatchMetricsSource="No"
    export DynamoDBCloudWatchMetricsSourceCategoryName="Dynamo/Existing/Metrics"

    # RDS App configuration
    export InstallRDSApp="No"
    export CreateRdsCloudWatchMetricsSource="No"
    export RdsCloudWatchMetricsSourceCategoryName="RDS/Existing/Metrics"

    # Lambda App Configuration
    export InstallLambdaApp="No"
    export CreateLambdaCloudTrailBucket="No"
    export LambdaCloudTrailLogsBucketName="lambda-all-randmomstring"
    export CreateLambdaCloudTrailLogSource="No"
    export LambdaCloudTrailCollectorName="lambda-my-collector"
    export LambdaCloudTrailLogsSourceName="lambda-my-source"
    export LambdaCloudTrailLogsSourceCategoryName="lambda/Existing/Logs"
    export CreateLambdaCloudWatchMetricsSource="No"
    export LambdaCloudWatchLogsCollectorName="lambda-my-collector-1"
    export LambdaCloudWatchLogsSourceName="lambda-my-source-1"
    export LambdaCloudWatchLogsSourceCategoryName="lambda/Existing/watch/Logs"
    export CreateLambdaCloudWatchLogsSource="No"
    export LambdaCloudWatchMetricsSourceCategoryName="lambda/Existing/metrics"

    # API Gateway App Configuration
    export InstallAPIGatewayApp="No"
    export CreateApiGatewayCloudTrailBucket="No"
    export ApiGatewayCloudTrailLogsBucketName="lambda-all-randmomstring"
    export CreateApiGatewayCloudTrailLogSource="No"
    export ApiGatewayCloudTrailCollectorName="api-my-collector"
    export ApiGatewayCloudTrailLogsSourceName="api-my-source"
    export ApiGatewayCloudTrailLogsSourceCategoryName="Api/Existing/logs"
    export CreateApiGatewayCloudWatchMetricsSource="No"
    export ApiGatewayCloudWatchMetricsSourceCategoryName="Api/Existing/Metrics"

    if [[ "${InstallType}" == "nothing" ]]
    then
        echo "nothing"
    elif [[ "${InstallType}" == "explorer" ]]
    then
        export CreateExplorerView="Yes"
    elif [[ "${InstallType}" == "ec2app" ]]
    then
        export InstallEC2App="Yes"
    elif [[ "${InstallType}" == "ec2withMeta" ]]
    then
        export InstallEC2App="Yes"
        export CreateMetaDataSource="Yes"
    elif [[ "${InstallType}" == "albapp" ]]
    then
        export InstallALBApp="Yes"
    elif [[ "${InstallType}" == "allalb" ]]
    then
        export InstallALBApp="Yes"
        export CreateS3Bucket="Yes"
        export CreateS3LogSource="Yes"
        export CreateAlbCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "alballwithexistingbucket" ]]
    then
        export InstallALBApp="Yes"
        export CreateS3Bucket="No"
        export CreateS3LogSource="Yes"
        export CreateAlbCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "dynamoapp" ]]
    then
        export InstallDynamoDBApp="Yes"
    elif [[ "${InstallType}" == "alldynamo" ]]
    then
        export InstallDynamoDBApp="Yes"
        export CreateDynamoDBCloudTrailBucket="Yes"
        export CreateDynamoDBCloudTrailLogSource="Yes"
        export CreateDynamoDBCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "dynamoallwithexistingbucket" ]]
    then
        export InstallDynamoDBApp="Yes"
        export CreateDynamoDBCloudTrailBucket="No"
        export CreateDynamoDBCloudTrailLogSource="Yes"
        export CreateDynamoDBCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "rdsapp" ]]
    then
        export InstallRDSApp="Yes"
    elif [[ "${InstallType}" == "rdscloudwatch" ]]
    then
        export InstallRDSApp="Yes"
        export CreateRdsCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "apiapp" ]]
    then
        export InstallAPIGatewayApp="Yes"
    elif [[ "${InstallType}" == "allapi" ]]
    then
        export InstallAPIGatewayApp="Yes"
        export CreateApiGatewayCloudTrailBucket="Yes"
        export CreateApiGatewayCloudTrailLogSource="Yes"
        export CreateApiGatewayCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "apiallwithexistingbucket" ]]
    then
        export InstallAPIGatewayApp="Yes"
        export CreateApiGatewayCloudTrailBucket="No"
        export CreateApiGatewayCloudTrailLogSource="Yes"
        export CreateApiGatewayCloudWatchMetricsSource="No"
    elif [[ "${InstallType}" == "lambdaapp" ]]
    then
        export InstallLambdaApp="Yes"
    elif [[ "${InstallType}" == "lambdall" ]]
    then
        export InstallLambdaApp="Yes"
        export CreateLambdaCloudTrailBucket="Yes"
        export CreateLambdaCloudTrailLogSource="Yes"
        export CreateLambdaCloudWatchMetricsSource="Yes"
        export CreateLambdaCloudWatchLogsSource="Yes"
    elif [[ "${InstallType}" == "lambdappwithexistingbucket" ]]
    then
        export InstallLambdaApp="Yes"
        export CreateLambdaCloudTrailBucket="No"
        export CreateLambdaCloudTrailLogSource="Yes"
        export CreateLambdaCloudWatchMetricsSource="No"
        export CreateLambdaCloudWatchLogsSource="No"
    elif [[ "${InstallType}" == "lambdappwithexistingbucket" ]]
    then
        export InstallLambdaApp="Yes"
        export CreateLambdaCloudTrailBucket="No"
        export CreateLambdaCloudTrailLogSource="No"
        export CreateLambdaCloudWatchMetricsSource="Yes"
        export CreateLambdaCloudWatchLogsSource="Yes"
    elif [[ "${InstallType}" == "allinstalls" ]]
    then
        export CreateExplorerView="Yes"
        export InstallEC2App="Yes"
        export CreateMetaDataSource="Yes"
        export InstallALBApp="Yes"
        export CreateS3Bucket="Yes"
        export CreateS3LogSource="Yes"
        export CreateAlbCloudWatchMetricsSource="Yes"
        export InstallDynamoDBApp="Yes"
        export CreateDynamoDBCloudTrailBucket="Yes"
        export CreateDynamoDBCloudTrailLogSource="Yes"
        export CreateDynamoDBCloudWatchMetricsSource="Yes"
        export InstallRDSApp="Yes"
        export CreateRdsCloudWatchMetricsSource="Yes"
        export InstallAPIGatewayApp="Yes"
        export CreateApiGatewayCloudTrailBucket="Yes"
        export CreateApiGatewayCloudTrailLogSource="Yes"
        export CreateApiGatewayCloudWatchMetricsSource="Yes"
        export InstallLambdaApp="Yes"
        export CreateLambdaCloudTrailBucket="Yes"
        export CreateLambdaCloudTrailLogSource="Yes"
        export CreateLambdaCloudWatchMetricsSource="Yes"
        export CreateLambdaCloudWatchLogsSource="Yes"
    elif [[ "${InstallType}" == "tagmetricrulesandApps" ]]
    then
        export InstallEC2App="Yes"
        export InstallALBApp="Yes"
        export InstallDynamoDBApp="Yes"
        export InstallRDSApp="Yes"
        export InstallAPIGatewayApp="Yes"
        export InstallLambdaApp="Yes"
    else
        echo "No Choice"
    fi

    # Export Sumo Properties
    export SumoAccessID=""
    export SumoAccessKey=""
    export SumoOrganizationId=""
    export SumoDeployment="nite"
    export RemoveSumoResourcesOnDeleteStack=true
    export AWSRegion="Current Region"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../../${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    AWSRegion="${AWSRegion}" InstallEC2App="${InstallEC2App}" InstallALBApp="${InstallALBApp}" InstallDynamoDBApp="${InstallDynamoDBApp}" \
    InstallRDSApp="${InstallRDSApp}" InstallLambdaApp="${InstallLambdaApp}" InstallAPIGatewayApp="${InstallAPIGatewayApp}" \
    CreateExplorerView="${CreateExplorerView}" ExplorerName="${ExplorerName}" AccountAlias="${AccountAlias}" \
    CreateMetaDataSource="${CreateMetaDataSource}" CreateS3Bucket="${CreateS3Bucket}" CreateS3LogSource="${CreateS3LogSource}" \
    CreateAlbCloudWatchMetricsSource="${CreateAlbCloudWatchMetricsSource}" CreateDynamoDBCloudTrailBucket="${CreateDynamoDBCloudTrailBucket}" \
    CreateDynamoDBCloudTrailLogSource="${CreateDynamoDBCloudTrailLogSource}" CreateDynamoDBCloudWatchMetricsSource="${CreateDynamoDBCloudWatchMetricsSource}" \
    CreateRdsCloudWatchMetricsSource="${CreateRdsCloudWatchMetricsSource}" CreateLambdaCloudTrailBucket="${CreateLambdaCloudTrailBucket}" \
    CreateLambdaCloudTrailLogSource="${CreateLambdaCloudTrailLogSource}" CreateLambdaCloudWatchMetricsSource="${CreateLambdaCloudWatchMetricsSource}" \
    CreateLambdaCloudWatchLogsSource="${CreateLambdaCloudWatchLogsSource}" CreateApiGatewayCloudTrailBucket="${CreateApiGatewayCloudTrailBucket}" \
    CreateApiGatewayCloudTrailLogSource="${CreateApiGatewayCloudTrailLogSource}" CreateApiGatewayCloudWatchMetricsSource="${CreateApiGatewayCloudWatchMetricsSource}" \
    Ec2AppSourceCategoryName="${Ec2AppSourceCategoryName}" S3LogsBucketName="${S3LogsBucketName}" AlbS3LogsCollectorName="${AlbS3LogsCollectorName}" \
    AlbS3LogsSourceName="${AlbS3LogsSourceName}" AlbS3LogsSourceCategoryName="${AlbS3LogsSourceCategoryName}" AlbCloudWatchMetricsSourceCategoryName="${AlbCloudWatchMetricsSourceCategoryName}" \
    DynamoDBCloudTrailLogsBucketName="${DynamoDBCloudTrailLogsBucketName}" DynamoDBCloudTrailCollectorName="${DynamoDBCloudTrailCollectorName}" \
    DynamoDBCloudTrailLogsSourceName="${DynamoDBCloudTrailLogsSourceName}" DynamoDBCloudTrailLogsSourceCategoryName="${DynamoDBCloudTrailLogsSourceCategoryName}" \
    DynamoDBCloudWatchMetricsSourceCategoryName="${DynamoDBCloudWatchMetricsSourceCategoryName}" RdsCloudWatchMetricsSourceCategoryName="${RdsCloudWatchMetricsSourceCategoryName}" \
    ApiGatewayCloudTrailLogsBucketName="${ApiGatewayCloudTrailLogsBucketName}" ApiGatewayCloudTrailCollectorName="${ApiGatewayCloudTrailCollectorName}" \
    ApiGatewayCloudTrailLogsSourceName="${ApiGatewayCloudTrailLogsSourceName}" ApiGatewayCloudTrailLogsSourceCategoryName="${ApiGatewayCloudTrailLogsSourceCategoryName}" \
    ApiGatewayCloudWatchMetricsSourceCategoryName="${ApiGatewayCloudWatchMetricsSourceCategoryName}" LambdaCloudTrailLogsBucketName="${LambdaCloudTrailLogsBucketName}" \
    LambdaCloudTrailCollectorName="${LambdaCloudTrailCollectorName}" LambdaCloudTrailLogsSourceName="${LambdaCloudTrailLogsSourceName}" \
    LambdaCloudTrailLogsSourceCategoryName="${LambdaCloudTrailLogsSourceCategoryName}" LambdaCloudWatchLogsCollectorName="${LambdaCloudWatchLogsCollectorName}" \
    LambdaCloudWatchLogsSourceName="${LambdaCloudWatchLogsSourceName}" LambdaCloudWatchLogsSourceCategoryName="${LambdaCloudWatchLogsSourceCategoryName}" \
    LambdaCloudWatchMetricsSourceCategoryName="${LambdaCloudWatchMetricsSourceCategoryName}"

done

echo "All Installation Complete for ${AppName}"