if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore20211221"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="appdevstore20211221-prod"
    AWS_REGION="us-east-1"
fi
sam package --template-file template.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged.yaml

sam deploy --template-file packaged.yaml --stack-name testingsecurityhubcollectorawsorg --capabilities CAPABILITY_IAM --region $AWS_REGION --parameter-overrides ParameterKey=SumoEndpoint,ParameterValue=https://endpoint6.collection.us2.sumologic.com/receiver/v1/http/

#aws --profile awsorg cloudformation describe-stack-events --stack-name testingsecurityhubcollectorawsorg --region $AWS_REGION
#aws --profile awsorg cloudformation get-template --stack-name testingsecurityhubcollectorawsorg  --region $AWS_REGION
#aws --profile awsorg serverlessrepo create-application-version --region us-east-1 --application-id arn:aws:serverlessrepo:us-east-1:$AWS_ACCOUNT_ID:applications/sumologic-securityhub-connector-aws-org --semantic-version 1.0.0 --template-body file://packaged.yaml