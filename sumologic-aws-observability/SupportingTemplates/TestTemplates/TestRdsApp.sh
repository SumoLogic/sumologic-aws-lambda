#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="rds_app"
export AppName="rds"
export InstallTypes=("all" "onlyapp")

for InstallType in "${InstallTypes[@]}"
do
    if [[ "${InstallType}" == "all" ]]
    then
        export CreateCloudWatchMetricsSource="Yes"
    elif [[ "${InstallType}" == "onlyapp" ]]
    then
        export CreateCloudWatchMetricsSource="No"
    else
        echo "No Choice"
    fi

    # Export Sumo Properties
    export SumoAccessID=""
    export SumoAccessKey=""
    export SumoOrganizationId=""
    export SumoDeployment="us1"
    export RemoveSumoResourcesOnDeleteStack=true

    # Export Collector Name
    export CollectorName="AWS-Sourabh-Collector${AppName}-${InstallType}"

    # Export CloudWatch Metrics Details
    export AWSRegion="Current Region"
    export CloudWatchMetricsSourceName="AWS-CloudWatch-Metrics-${AppName}-${InstallType}-Source"
    export CloudWatchMetricsSourceCategoryName="AWS/CloudWatch/${AppName}/${InstallType}/Metrics"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    CollectorName="${CollectorName}" AWSRegion="${AWSRegion}" CloudWatchMetricsSourceName="${CloudWatchMetricsSourceName}" \
    CloudWatchMetricsSourceCategoryName="${CloudWatchMetricsSourceCategoryName}" \
    CreateCloudWatchMetricsSource="${CreateCloudWatchMetricsSource}"

done

echo "All Installation Complete for ${AppName}"