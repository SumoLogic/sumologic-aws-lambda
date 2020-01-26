#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="sumologic_observability.master"
export AppName="master"
export InstallTypes=("nothing" "explorer")

for InstallType in "${InstallTypes[@]}"
do
    export AccountAlias="test-master-${InstallType}"

    export CreateExplorerView="No"
    export InstallEC2App="No"
    export InstallALBApp="No"
    export InstallDynamoDBApp="No"
    export InstallRDSApp="No"
    export InstallLambdaApp="No"
    export InstallAPIGatewayApp="No"
    export CreateMetaDataSource="No"
    export CreateS3Bucket="No"
    export CreateS3LogSource="No"
    export CreateAlbCloudWatchMetricsSource="No"
    export CreateDynamoDBCloudTrailBucket="No"
    export CreateDynamoDBCloudTrailLogSource="No"
    export CreateDynamoDBCloudWatchMetricsSource="No"
    export CreateRdsCloudWatchMetricsSource="No"
    export CreateLambdaCloudTrailBucket="No"
    export CreateLambdaCloudTrailLogSource="No"
    export CreateLambdaCloudWatchMetricsSource="No"
    export CreateLambdaCloudWatchLogsSource="No"
    export CreateApiGatewayCloudTrailBucket="No"
    export CreateApiGatewayCloudTrailLogSource="No"
    export CreateApiGatewayCloudWatchMetricsSource="No"

    if [[ "${InstallType}" == "nothing" ]]
    then
        echo "nothing"
    elif [[ "${InstallType}" == "explorer" ]]
    then
        export CreateExplorerView="Yes"
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

    # Export Explorer Option
    export ExplorerName="AWS Explorer Test View"

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
    CreateApiGatewayCloudTrailLogSource="${CreateApiGatewayCloudTrailLogSource}" CreateApiGatewayCloudWatchMetricsSource="${CreateApiGatewayCloudWatchMetricsSource}"

done

echo "All Installation Complete for ${AppName}"