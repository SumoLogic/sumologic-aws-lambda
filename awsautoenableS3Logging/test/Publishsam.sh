#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="default"

if [[ "${AWS_PROFILE}" == "personal" ]]
then
    SAM_S3_BUCKET="sumologiclambdahelper-us-east-1"
else
    SAM_S3_BUCKET="appdevstore"
fi

# define all application names that needs to be published.
app_names=(
    "AutoEnableS3Logs:sumologic-s3-logging-auto-enable.yaml"
)

echo `sam --version`
# Regex to deploy only expected templates.
match_case="AutoEnableS3Logs"

for app_name in ${app_names[@]}
do
    KEY="${app_name%%:*}"
    VALUE="${app_name##*:}"

    if [[ "${KEY}" == *"${match_case}"* ]]; then
        # Grep Version from the SAM Template.
        export version=`grep AWS::ServerlessRepo::Application: ../${VALUE} -A 20 | grep SemanticVersion | cut -d ':' -f 2 | xargs`
        echo "Package and publish the Template file ${VALUE} with version ${version}."

        echo `sam validate -t ../${VALUE}`

        sam package --profile ${AWS_PROFILE} --template-file ../${VALUE} --s3-bucket ${SAM_S3_BUCKET} --output-template-file ../packaged.yaml \
        --s3-prefix "${KEY}/v${version}"

        sam publish --template ../packaged.yaml --region ${AWS_REGION} --semantic-version ${version}
        echo "Publish done"
    fi
done

