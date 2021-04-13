#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"

if [[ "${AWS_PROFILE}" == "personal" ]]
then
    SAM_S3_BUCKET="cf-templates-1qpf3unpuo1hw-us-east-1"
else
    SAM_S3_BUCKET="appdevstore"
fi

# define all application names that needs to be published.
app_names=(
    "GuardDuty:template.yaml"
    "guarddutybenchmark:template_V2.yaml"
)

sam --version
# Regex to deploy only expected templates.
match_case=""

for app_name in "${app_names[@]}"
do
    KEY="${app_name%%:*}"
    VALUE="${app_name##*:}"

    if [[ "${KEY}" == *"${match_case}"* ]]; then
        # Grep Version from the SAM Template.
        version=$(grep AWS::ServerlessRepo::Application: ../"${KEY}/${VALUE}" -A 20 | grep SemanticVersion | cut -d ':' -f 2 | xargs)
        echo "Package and publish the Template file ${VALUE} with version ${version}."

        sam validate -t ../"${KEY}/${VALUE}"

        sam package --profile ${AWS_PROFILE} --template-file ../"${KEY}/${VALUE}" --s3-bucket ${SAM_S3_BUCKET}  --output-template-file ../"${KEY}"/packaged.yaml \
        --s3-prefix "${KEY}/v${version}"

        sam publish --template ../"${KEY}"/packaged.yaml --region ${AWS_REGION} --semantic-version "${version}"
        echo "Publish done"
    fi
done
