if [ "$AWS_PROFILE" == "prod" ]
then
    SAM_S3_BUCKET="appdevstore"
    AWS_REGION="us-east-1"
else
    SAM_S3_BUCKET="appstore-20231030-securityhub-collector-awsorg"
    AWS_REGION="us-east-1"
fi
sam package --template-file template.yaml --s3-bucket $SAM_S3_BUCKET  --output-template-file packaged.yaml

sam publish --template packaged.yaml --region us-east-1

# sam deploy --template-file packaged.yaml --stack-name testingsecurityhubcollectorawsorg --capabilities CAPABILITY_IAM --region $AWS_REGION --parameter-overrides ParameterKey=SumoEndpoint,ParameterValue=https://endpoint6.collection.us2.sumologic.com/receiver/v1/http/

#aws --profile awsorg cloudformation describe-stack-events --stack-name testingsecurityhubcollectorawsorg --region $AWS_REGION
#aws --profile awsorg cloudformation get-template --stack-name testingsecurityhubcollectorawsorg  --region $AWS_REGION
