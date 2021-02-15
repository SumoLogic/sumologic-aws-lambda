#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"

# Update the bucket value based on aws account you are deploying SAM app in.
if [[ "${AWS_PROFILE}" == "personal" ]]
then
    SAM_S3_BUCKET="sumologic-aws-observability-templates"
else
    SAM_S3_BUCKET="appdevstore"
fi

# define all application names that needs to be published.
app_names=(
    "KinesisFirehoseCWLogs:logs" "KinesisFirehoseCWMetrics:metrics"
)

echo `sam --version`
# Regex to deploy only expected templates.
match_case="KinesisFirehose"

for app_name in "${app_names[@]}"
do
    KEY="${app_name%%:*}"
    VALUE="${app_name##*:}"

    template_path="${VALUE}/${KEY}.template.yaml"
    packaged_path="${VALUE}/packaged.yaml"

    if [[ "${KEY}" == *"${match_case}"* ]]; then
        # Grep Version from the SAM Template.
        export version=`grep AWS::ServerlessRepo::Application: ../${template_path} -A 20 | grep SemanticVersion | cut -d ':' -f 2 | xargs`
        echo "Package and publish the Template file ${KEY} with version ${version}."

        echo `sam validate -t ../${template_path}`

        sam package --profile ${AWS_PROFILE} --template-file ../${template_path} --s3-bucket ${SAM_S3_BUCKET} --output-template-file ../${packaged_path} \
        --s3-prefix "${KEY}/v${version}"

        sam publish --template ../${packaged_path} --region ${AWS_REGION} --semantic-version ${version} --profile ${AWS_PROFILE}
        echo "Publish done"
    fi
done

