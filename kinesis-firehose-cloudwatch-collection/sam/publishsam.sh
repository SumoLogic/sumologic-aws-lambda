#!/bin/bash

export AWS_REGION="us-east-1"
# IMPORTANT - Update the profile where you would like to deploy SAM app.
export AWS_PROFILE="personal"

# IMPORTANT - Update the bucket value based on aws account you are deploying SAM app in.
if [[ "${AWS_PROFILE}" == "personal" ]]
then
    SAM_S3_BUCKET="<provide your bucket name>"
else
    SAM_S3_BUCKET="appdevstore"
fi

# define all application names that needs to be published.
app_names=(
    "KinesisFirehoseCWLogs:logs" "KinesisFirehoseCWMetrics:metrics"
)

sam --version

# Regex to deploy only expected templates.
match_case="KinesisFirehoseCWMetrics"

for app_name in "${app_names[@]}"
do
    KEY="${app_name%%:*}"
    VALUE="${app_name##*:}"

    template_path="${KEY}.template.yaml"
    packaged_path="packaged.yaml"

    if [[ "${KEY}" == *"${match_case}"* ]]; then
        # Grep Version from the SAM Template.
        cd ../"${VALUE}" || exit

        export version=`grep AWS::ServerlessRepo::Application: ${template_path} -A 20 | grep SemanticVersion | cut -d ':' -f 2 | xargs`
        echo "Package and publish the Template file ${KEY} with version ${version}."

        sam validate -t ${template_path}

        sam build -t ${template_path}

        sam package --profile ${AWS_PROFILE} --template-file .aws-sam/build/template.yaml --s3-bucket ${SAM_S3_BUCKET} --output-template-file ${packaged_path} \
        --s3-prefix "${KEY}/v${version}"

        sam publish --template ${packaged_path} --region ${AWS_REGION} --semantic-version ${version} --profile ${AWS_PROFILE}
        echo "Publish done"
    fi
    cd ../sam || exit
done

