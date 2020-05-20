#!/bin/sh

echo "Testing for Master Template....................."

export AWS_REGION=$1
export AWS_PROFILE=$2
export TEMPLATE_S3_BUCKET="cf-templates-1qpf3unpuo1hw-ap-south-1"
# App to test
export AppName=$3
export InstallType=$4

export uid=`cat /dev/random | LC_CTYPE=C tr -dc "[:lower:]" | head -c 6`

# Sumo Logic Access Configuration
export Section1aSumoLogicDeployment=$5
export Section1bSumoLogicAccessID=$6
export Section1cSumoLogicAccessKey=$7
export Section1dSumoLogicOrganizationId=$8
export Section1eSumoLogicResourceRemoveOnDeleteStack=true

export Section2cAccountAlias=${InstallType}
export Section2dTagAWSResourcesFilterExpression=".*"
export Section5bCloudWatchMetricsNameSpaces=""
export Section6bALBS3LogsBucketName="${AppName}-${InstallType}-${uid}"
export Section6cALBS3BucketPathExpression="*"
export Section6eALBS3LogsCollectorName=""
export Section6fALBLogsSourceName="sourabh-source-alb-${AppName}-${InstallType}"
export Section6gALBLogsSourceCategoryName="Labs/alb/${AppName}/${InstallType}"
export Section7bCloudTrailLogsBucketName="${AppName}-${InstallType}-${uid}"
export Section7cCloudTrailBucketPathExpression="*"
export Section7eCloudTrailCollectorName=""
export Section7fCloudTrailLogsSourceName="sourabh-source-cloudtrail-${AppName}-${InstallType}"
export Section7gCloudTrailLogsSourceCategoryName="aws/observability/cloudtrail/logs"
export Section8bLambdaCloudWatchLogsCollectorName=""
export Section8cLambdaCloudWatchLogsSourceName="sourabh-source-cloudwatch-${AppName}-${InstallType}"
export Section8dLambdaCloudWatchLogsSourceCategoryName="Labs/cloudwatch/${AppName}/${InstallType}"
export Section9bAutoEnableS3LogsFilterExpression=".*"
export Section9dAutoSubscribeLambdaLogGroupPattern=".*"

export Section2aTagAWSResourcesOptions="None"
export Section2bAWSResourcesList=""
export Section3aEC2InstallApp="No"
export Section3bALBInstallApp="No"
export Section3cDynamoDBInstallApp="No"
export Section3dRDSInstallApp="No"
export Section3eLambdaInstallApp="No"
export Section3fAPIGatewayInstallApp="No"
export Section4aEC2CreateMetaDataSource="No"
export Section5aCreateCloudWatchMetricsSource="No"
export Section6aALBCreateS3Bucket="No"
export Section6dALBCreateLogSource="No"
export Section7aCreateCloudTrailBucket="No"
export Section7dCreateCloudTrailLogSource="No"
export Section8aLambdaCreateCloudWatchLogsSource="No"
export Section9aAutoEnableS3LogsALBResourcesOptions="None"
export Section9cAutoSubscribeLogGroupsLambdaOptions="None"

# By Default, we create explorer view, Metric Rules and FER, as we need them for each case.
# Stack Name
export stackName="${AppName}-${InstallType}"

# onlyapps - Installs only the apps in Sumo Logic.
if [[ "${InstallType}" == "onlyapps" ]]
then
    export Section3aEC2InstallApp="Yes"
    export Section3bALBInstallApp="Yes"
    export Section3cDynamoDBInstallApp="Yes"
    export Section3dRDSInstallApp="Yes"
    export Section3eLambdaInstallApp="Yes"
    export Section3fAPIGatewayInstallApp="Yes"
# someapps - Installs some apps in Sumo Logic.
elif [[ "${InstallType}" == "someapps" ]]
then
    export Section3aEC2InstallApp="Yes"
    export Section3bALBInstallApp="Yes"
    export Section3dRDSInstallApp="Yes"
    export Section3fAPIGatewayInstallApp="Yes"
# onlytagging - Tags only the existing resources. Alb, dynamo, api
elif [[ "${InstallType}" == "onlytaggingexisting" ]]
then
    export Section2aTagAWSResourcesOptions="Existing"
    export Section2bAWSResourcesList="alb, dynamodb, apigateway"
# onlytagging - Tags only the new resources. rds, lambda, ec2
elif [[ "${InstallType}" == "onlytaggingnew" ]]
then
    export Section2aTagAWSResourcesOptions="New"
    export Section2bAWSResourcesList="ec2, rds, lambda"
# onlytagging - Tags both existing and the new resources. all.
elif [[ "${InstallType}" == "onlytagging" ]]
then
    export Section2aTagAWSResourcesOptions="Both"
    export Section2bAWSResourcesList="ec2, alb, dynamodb, apigateway, rds, lambda"
# onlys3autoenableexisting - Enable S3 logging for existing ALB. Needs an existing bucket or takes if new bucket is created otherwise stack creation fails.
elif [[ "${InstallType}" == "onlys3autoenableexisting" ]]
then
    export Section9aAutoEnableS3LogsALBResourcesOptions="Existing"
    export Section6bALBS3LogsBucketName="sumologiclambdahelper-${AWS_REGION}"
# onlys3autoenablenew - Enable S3 logging for new ALB. Needs an existing bucket or takes if new bucket is created otherwise stack creation fails.
elif [[ "${InstallType}" == "onlys3autoenablenew" ]]
then
    export Section9aAutoEnableS3LogsALBResourcesOptions="New"
    export Section6bALBS3LogsBucketName="sumologiclambdahelper-${AWS_REGION}"
# onlys3autoenable - Enable S3 logging for both ALB. Needs an existing bucket or takes if new bucket is created otherwise stack creation fails.
elif [[ "${InstallType}" == "onlys3autoenable" ]]
then
    export Section9aAutoEnableS3LogsALBResourcesOptions="Both"
    export Section6bALBS3LogsBucketName="sumologiclambdahelper-${AWS_REGION}"
# onlyec2source - Only Creates the EC2 metadata Source.
elif [[ "${InstallType}" == "onlyec2source" ]]
then
    export Section4aEC2CreateMetaDataSource="Yes"
# onlymetricssourceemptyname - Only Creates the CloudWatch Metrics Source with "" EMPTY namespaces.
elif [[ "${InstallType}" == "onlymetricssourceemptyname" ]]
then
    export Section5aCreateCloudWatchMetricsSource="Yes"
    export Section5bCloudWatchMetricsNameSpaces=""
# onlymetricssourcewithname - Only Creates the CloudWatch Metrics Source with namespaces AWS/ApplicationELB, AWS/ApiGateway, AWS/DynamoDB, AWS/Lambda, AWS/RDS.
elif [[ "${InstallType}" == "onlymetricssourcewithname" ]]
then
    export Section5aCreateCloudWatchMetricsSource="Yes"
    export Section5bCloudWatchMetricsNameSpaces="AWS/ApplicationELB, AWS/ApiGateway, AWS/DynamoDB, AWS/Lambda, AWS/RDS"
# onlycloudtrailwithbucket - Only Creates the CloudTrail Logs Source with new Bucket.
elif [[ "${InstallType}" == "onlycloudtrailwithbucket" ]]
then
    export Section7aCreateCloudTrailBucket="Yes"
    export Section7dCreateCloudTrailLogSource="Yes"
# onlycloudtrailexisbucket - Only Creates the CloudTrail Logs Source with existing Bucket. If no "" empty bucket provided with empty bucket name, it fails.
elif [[ "${InstallType}" == "onlycloudtrailexisbucket" ]]
then
    export Section7dCreateCloudTrailLogSource="Yes"
    export Section7cCloudTrailBucketPathExpression="AWSLogs/Sourabh/Test"
    export Section7bCloudTrailLogsBucketName="sumologiclambdahelper-${AWS_REGION}"
# updatecloudtrailsource - Only updates the CloudTrail Logs Source with if Collector name and source name is provided.
elif [[ "${InstallType}" == "updatecloudtrailsource" ]]
then
    export Section7eCloudTrailCollectorName="aws-observability-collector"
    export Section7fCloudTrailLogsSourceName="onlycloudtrailexisbucket-aws-observability-cloudtrail-${AWS_REGION}"
# cwlogssourceonly - Creates a Cloudwatch logs source, with lambda function of log group connector.
elif [[ "${InstallType}" == "cwlogssourceonly" ]]
then
    export Section8aLambdaCreateCloudWatchLogsSource="Yes"
# cwlogssourcenewlambdaautosub - Creates a Cloudwatch logs source, with lambda function of log group connector with auto subscribe only for new lambda.
elif [[ "${InstallType}" == "cwlogssourcenewlambdaautosub" ]]
then
    export Section8aLambdaCreateCloudWatchLogsSource="Yes"
    export Section9cAutoSubscribeLogGroupsLambdaOptions="New"
# cwlogssourceexitlambdaautosub - Creates a Cloudwatch logs source, with lambda function of log group connector WITHOUT auto subscribe only for new lambda.
elif [[ "${InstallType}" == "cwlogssourceexitlambdaautosub" ]]
then
    export Section8aLambdaCreateCloudWatchLogsSource="Yes"
    export Section9cAutoSubscribeLogGroupsLambdaOptions="Existing"
# cwlogssourcebothlambdaautosub - Creates a Cloudwatch logs source, with lambda function of log group connector WITH auto subscribe only for new and existing lambda.
elif [[ "${InstallType}" == "cwlogssourcebothlambdaautosub" ]]
then
    export Section8aLambdaCreateCloudWatchLogsSource="Yes"
    export Section9cAutoSubscribeLogGroupsLambdaOptions="Both"
    export Section9dAutoSubscribeLambdaLogGroupPattern="lambda"
# cwlogssourcebothlambdaautosub - update the cloudwatch source if collector name and source name is provided.
elif [[ "${InstallType}" == "updatecwlogssource" ]]
then
    export Section8bLambdaCloudWatchLogsCollectorName="aws-observability-collector"
    export Section8cLambdaCloudWatchLogsSourceName="cwlogssourceexitlambdaautosub-aws-observability-cloudwatch-logs-${AWS_REGION}"
# albsourcewithbukcetwithauto - Creates only ALB source with new bucket along with auto subscribe.
elif [[ "${InstallType}" == "albsourcewithbukcetwithauto" ]]
then
    export Section6aALBCreateS3Bucket="Yes"
    export Section6dALBCreateLogSource="Yes"
    export Section9aAutoEnableS3LogsALBResourcesOptions="Both"
# albsourceexistingbukcet - Creates only ALB source with new existing bucket.
elif [[ "${InstallType}" == "albsourceexistingbukcet" ]]
then
    export Section6dALBCreateLogSource="Yes"
    export Section6bALBS3LogsBucketName="sumologiclambdahelper-${AWS_REGION}"
    export Section6cALBS3BucketPathExpression="Labs/ALB/sourabh"
# updatealbsource - updates only ALB source with provided collector and source.
elif [[ "${InstallType}" == "updatealbsource" ]]
then
    export Section6eALBS3LogsCollectorName="aws-observability-collector"
    export Section6fALBLogsSourceName="albsourcewithbukcetwithauto-aws-observability-alb-${AWS_REGION}"
# onlysources - creates all sources with common bucket creation for ALB and CloudTrail with auto enable option.
elif [[ "${InstallType}" == "onlysources" ]]
then
    export Section4aEC2CreateMetaDataSource="Yes"
    export Section5aCreateCloudWatchMetricsSource="Yes"
    export Section6dALBCreateLogSource="Yes"
    export Section6aALBCreateS3Bucket="Yes"
    export Section7dCreateCloudTrailLogSource="Yes"
    export Section7aCreateCloudTrailBucket="Yes"
    export Section8aLambdaCreateCloudWatchLogsSource="Yes"
    export Section9aAutoEnableS3LogsALBResourcesOptions="Existing"
# albexistingcloudtrialnew - creates ALB source with existing bucket and CloudTrail with new bucket. Create CW metrics source also.
elif [[ "${InstallType}" == "albexistingcloudtrialnew" ]]
then
    export Section5aCreateCloudWatchMetricsSource="Yes"
    export Section5bCloudWatchMetricsNameSpaces="AWS/ApplicationELB, AWS/ApiGateway"
    export Section6dALBCreateLogSource="Yes"
    export Section6bALBS3LogsBucketName="sumologiclambdahelper-${AWS_REGION}"
    export Section6cALBS3BucketPathExpression="Labs/ALB/asasdas"
    export Section7dCreateCloudTrailLogSource="Yes"
    export Section7aCreateCloudTrailBucket="Yes"
# albnewcloudtrialexisting - creates ALB source with new bucket and CloudTrail with Existing bucket. Create EC2 source also.
elif [[ "${InstallType}" == "albnewcloudtrialexisting" ]]
then
    export Section4aEC2CreateMetaDataSource="Yes"
    export Section6dALBCreateLogSource="Yes"
    export Section6aALBCreateS3Bucket="Yes"
    export Section7dCreateCloudTrailLogSource="Yes"
    export Section7cCloudTrailBucketPathExpression="AWSLogs/Sourabh/Test"
    export Section7bCloudTrailLogsBucketName="sumologiclambdahelper-${AWS_REGION}"
# albec2apiappall - creates everything for EC2, ALB and API Gateway apps.
elif [[ "${InstallType}" == "albec2apiappall" ]]
then
    export Section3aEC2InstallApp="Yes"
    export Section3bALBInstallApp="Yes"
    export Section3fAPIGatewayInstallApp="Yes"
    export Section2aTagAWSResourcesOptions="Both"
    export Section2bAWSResourcesList="ec2, alb, apigateway"
    export Section9aAutoEnableS3LogsALBResourcesOptions="Both"
    export Section4aEC2CreateMetaDataSource="Yes"
    export Section5aCreateCloudWatchMetricsSource="Yes"
    export Section5bCloudWatchMetricsNameSpaces="AWS/ApplicationELB, AWS/ApiGateway"
    export Section6aALBCreateS3Bucket="Yes"
    export Section6dALBCreateLogSource="Yes"
    export Section7dCreateCloudTrailLogSource="Yes"
    export Section7aCreateCloudTrailBucket="Yes"
# rdsdynamolambdaappall - creates everything for RDS, DYNAMO DB and LAMBDA apps.
elif [[ "${InstallType}" == "rdsdynamolambdaappall" ]]
then
    export Section3cDynamoDBInstallApp="Yes"
    export Section3dRDSInstallApp="Yes"
    export Section3eLambdaInstallApp="Yes"
    export Section2aTagAWSResourcesOptions="Both"
    export Section2bAWSResourcesList="dynamodb, rds, lambda"
    export Section9cAutoSubscribeLogGroupsLambdaOptions="Both"
    export Section9dAutoSubscribeLambdaLogGroupPattern="lambda"
    export Section5aCreateCloudWatchMetricsSource="Yes"
    export Section5bCloudWatchMetricsNameSpaces="AWS/DynamoDB, AWS/Lambda, AWS/RDS"
    export Section7dCreateCloudTrailLogSource="Yes"
    export Section7aCreateCloudTrailBucket="Yes"
    export Section8aLambdaCreateCloudWatchLogsSource="Yes"
# onlyappswithexistingsources - Install Apps with existing sources. This should Update the CloudTrail, CloudWatch and ALB sources.
elif [[ "${InstallType}" == "onlyappswithexistingsources" ]]
then
    export Section3cDynamoDBInstallApp="Yes"
    export Section3dRDSInstallApp="Yes"
    export Section3eLambdaInstallApp="Yes"
    export Section3aEC2InstallApp="Yes"
    export Section3bALBInstallApp="Yes"
    export Section3fAPIGatewayInstallApp="Yes"
    export Section2aTagAWSResourcesOptions="Both"
    export Section2bAWSResourcesList="ec2, alb, apigateway, dynamodb, rds, lambda"
    export Section9aAutoEnableS3LogsALBResourcesOptions="Both"
    export Section6bALBS3LogsBucketName="sumologiclambdahelper-${AWS_REGION}"
    export Section9cAutoSubscribeLogGroupsLambdaOptions="Both"
    export Section9dAutoSubscribeLambdaLogGroupPattern="lambda"
    export Section6eALBS3LogsCollectorName="aws-observability-collector"
    export Section6fALBLogsSourceName="defaultparameters-aws-observability-alb-${AWS_REGION}"
    export Section8bLambdaCloudWatchLogsCollectorName="aws-observability-collector"
    export Section8cLambdaCloudWatchLogsSourceName="defaultparameters-aws-observability-cloudwatch-logs-${AWS_REGION}"
    export Section7eCloudTrailCollectorName="aws-observability-collector"
    export Section7fCloudTrailLogsSourceName="defaultparameters-aws-observability-cloudtrail-${AWS_REGION}"
# defaultparameters - Install CF with default parameters.
elif [[ "${InstallType}" == "defaultparameters" ]]
then
    echo "Doing Default Installation .............................."
    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./templates/sumologic_observability.master.template.yaml --region ${AWS_REGION} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
    --parameter-overrides Section1aSumoLogicDeployment="${Section1aSumoLogicDeployment}" Section1bSumoLogicAccessID="${Section1bSumoLogicAccessID}" \
    Section1cSumoLogicAccessKey="${Section1cSumoLogicAccessKey}" Section1dSumoLogicOrganizationId="${Section1dSumoLogicOrganizationId}" \
    Section1eSumoLogicResourceRemoveOnDeleteStack="${Section1eSumoLogicResourceRemoveOnDeleteStack}" Section2cAccountAlias="${Section2cAccountAlias}"
else
    echo "No Valid Choice."
fi

if [[ "${InstallType}" != "defaultparameters" ]]
then
    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./templates/sumologic_observability.master.template.yaml --region ${AWS_REGION} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
    --parameter-overrides Section1aSumoLogicDeployment="${Section1aSumoLogicDeployment}" Section1bSumoLogicAccessID="${Section1bSumoLogicAccessID}" \
    Section1cSumoLogicAccessKey="${Section1cSumoLogicAccessKey}" Section1dSumoLogicOrganizationId="${Section1dSumoLogicOrganizationId}" \
    Section1eSumoLogicResourceRemoveOnDeleteStack="${Section1eSumoLogicResourceRemoveOnDeleteStack}" Section2cAccountAlias="${Section2cAccountAlias}" \
    Section2dTagAWSResourcesFilterExpression="${Section2dTagAWSResourcesFilterExpression}" Section5bCloudWatchMetricsNameSpaces="${Section5bCloudWatchMetricsNameSpaces}" \
    Section6bALBS3LogsBucketName="${Section6bALBS3LogsBucketName}" Section6cALBS3BucketPathExpression="${Section6cALBS3BucketPathExpression}" \
    Section6eALBS3LogsCollectorName="${Section6eALBS3LogsCollectorName}" Section6fALBLogsSourceName="${Section6fALBLogsSourceName}" \
    Section6gALBLogsSourceCategoryName="${Section6gALBLogsSourceCategoryName}" Section7bCloudTrailLogsBucketName="${Section7bCloudTrailLogsBucketName}" \
    Section7cCloudTrailBucketPathExpression="${Section7cCloudTrailBucketPathExpression}" Section7eCloudTrailCollectorName="${Section7eCloudTrailCollectorName}" \
    Section7fCloudTrailLogsSourceName="${Section7fCloudTrailLogsSourceName}" Section7gCloudTrailLogsSourceCategoryName="${Section7gCloudTrailLogsSourceCategoryName}" \
    Section8bLambdaCloudWatchLogsCollectorName="${Section8bLambdaCloudWatchLogsCollectorName}" Section8cLambdaCloudWatchLogsSourceName="${Section8cLambdaCloudWatchLogsSourceName}" \
    Section8dLambdaCloudWatchLogsSourceCategoryName="${Section8dLambdaCloudWatchLogsSourceCategoryName}" \
    Section9bAutoEnableS3LogsFilterExpression="${Section9bAutoEnableS3LogsFilterExpression}" Section9dAutoSubscribeLambdaLogGroupPattern="${Section9dAutoSubscribeLambdaLogGroupPattern}" \
    Section2aTagAWSResourcesOptions="${Section2aTagAWSResourcesOptions}" Section2bAWSResourcesList="${Section2bAWSResourcesList}" \
    Section3aEC2InstallApp="${Section3aEC2InstallApp}" Section3bALBInstallApp="${Section3bALBInstallApp}" Section3cDynamoDBInstallApp="${Section3cDynamoDBInstallApp}" \
    Section3dRDSInstallApp="${Section3dRDSInstallApp}" Section3eLambdaInstallApp="${Section3eLambdaInstallApp}" Section3fAPIGatewayInstallApp="${Section3fAPIGatewayInstallApp}" \
    Section4aEC2CreateMetaDataSource="${Section4aEC2CreateMetaDataSource}" Section5aCreateCloudWatchMetricsSource="${Section5aCreateCloudWatchMetricsSource}" \
    Section6aALBCreateS3Bucket="${Section6aALBCreateS3Bucket}" Section6dALBCreateLogSource="${Section6dALBCreateLogSource}" \
    Section7aCreateCloudTrailBucket="${Section7aCreateCloudTrailBucket}" Section7dCreateCloudTrailLogSource="${Section7dCreateCloudTrailLogSource}" \
    Section8aLambdaCreateCloudWatchLogsSource="${Section8aLambdaCreateCloudWatchLogsSource}" \
    Section9aAutoEnableS3LogsALBResourcesOptions="${Section9aAutoEnableS3LogsALBResourcesOptions}" \
    Section9cAutoSubscribeLogGroupsLambdaOptions="${Section9cAutoSubscribeLogGroupsLambdaOptions}"
fi