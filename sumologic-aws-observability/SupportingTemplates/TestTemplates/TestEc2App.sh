#!/bin/bash

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppTemplateName="ec2_metrics_app"
export AppName="ec2"
export InstallTypes=("all" "onlyapp")

for InstallType in "${InstallTypes[@]}"
do
    if [[ "${InstallType}" == "all" ]]
    then
        export CreateMetaDataSource="Yes"
    elif [[ "${InstallType}" == "onlyapp" ]]
    then
        export CreateMetaDataSource="No"
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

    # Export MetaData Source Details
    export AWSRegion="Current Region"
    export MetaDataSourceName="AWS-MetaData-${AppName}-${InstallType}-Source"
    export MetricsSourceCategoryName="hostmetrics"

    export template_file="${AppTemplateName}.template.yaml"

    aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ././../${template_file} \
    --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name "${AppName}-${InstallType}" \
    --parameter-overrides SumoDeployment="${SumoDeployment}" SumoAccessID="${SumoAccessID}" SumoAccessKey="${SumoAccessKey}" \
    SumoOrganizationId="${SumoOrganizationId}" RemoveSumoResourcesOnDeleteStack="${RemoveSumoResourcesOnDeleteStack}" \
    CollectorName="${CollectorName}" AWSRegion="${AWSRegion}" MetaDataSourceName="${MetaDataSourceName}" \
    MetricsSourceCategoryName="${MetricsSourceCategoryName}" \
    CreateMetaDataSource="${CreateMetaDataSource}"

done

echo "All Installation Complete for ${AppName}"