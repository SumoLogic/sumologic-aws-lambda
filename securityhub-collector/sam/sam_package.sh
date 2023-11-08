echo "Using AWS_PROFILE: $AWS_PROFILE"
if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="appstore-20231108-securityhub-collector"
    AWS_REGION="us-east-2"
fi

version="1.0.9"
echo "Creating package.yaml"
sam package --template-file template.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged.yaml --s3-prefix "SecurityHubCollector/v"$version --region $AWS_REGION --profile $AWS_PROFILE

if [ $? -ne 0 ]
then
    echo "Creating package command failed!"
    exit 1
else
    echo "package.yaml created"
fi

echo "Publishing sumologic-securityhub-collector "$version
sam publish --template packaged.yaml --region $AWS_REGION --semantic-version $version

# sam deploy --template-file packaged.yaml --stack-name testingsechubcollector --capabilities CAPABILITY_IAM --region $AWS_REGION --parameter-overrides S3SourceBucketName=securityhubfindings

echo "Published sumologic-securityhub-collector "$version

#aws cloudformation describe-stack-events --stack-name testingsecurityhublambda --region $AWS_REGION
#aws cloudformation get-template --stack-name testingsecurityhublambda  --region $AWS_REGION
# aws serverlessrepo create-application-version --region us-east-1 --application-id arn:aws:serverlessrepo:us-east-1:$AWS_ACCOUNT_ID:applications/sumologic-securityhub-collector --semantic-version 1.0.1 --template-body file://packaged.yaml
