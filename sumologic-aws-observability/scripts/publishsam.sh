#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"

if [[ "${AWS_PROFILE}" == "personal" ]]
then
    SAM_S3_BUCKET="sumologiclambdahelper-us-east-1"
else
    SAM_S3_BUCKET="appdevstore"
fi

# define all application names that needs to be published.
app_names=(
    "alb:alb_app.template.yaml"
    "rds:rds_app.template.yaml"
    "apigateway:api_gateway_app.template.yaml"
    "dynamodb:dynamodb_app.template.yaml"
    "ec2metrics:ec2_metrics_app.template.yaml"
    "lambda:lambda_app.template.yaml"
    "AutoEnableS3LogsAlb:auto_enable_s3_alb.template.yaml"
)

echo `sam --version`
# Regex to deploy only expected templates.
match_case="ec2metrics"

for app_name in ${app_names[@]}
do
    KEY="${app_name%%:*}"
    VALUE="${app_name##*:}"

    if [[ "${KEY}" == *"${match_case}"* ]]; then
        # Grep Version from the SAM Template.
        export version=`grep AWS::ServerlessRepo::Application: ./${KEY}/sam/${VALUE} -A 20 | grep SemanticVersion | cut -d ':' -f 2 | xargs`
        echo "Package and publish the Template file ${VALUE} with version ${version}."

        echo `sam validate -t ./${KEY}/sam/${VALUE}`

        sam package --profile ${AWS_PROFILE} --template-file ./${KEY}/sam/${VALUE} --s3-bucket ${SAM_S3_BUCKET}  --output-template-file ./${KEY}/sam/packaged.yaml \
        --s3-prefix "aws-observability/${KEY}/v${version}"

        sam publish --template ./${KEY}/sam/packaged.yaml --region ${AWS_REGION} --semantic-version ${version}
        echo "Publish done"
    fi
done

