#!/bin/sh

export AWS_REGION="us-east-1"
export AWS_PROFILE="personal"
# App to test
export AppName=sample
export InstallType="installexplorerviews"

export uid_1=`cat /dev/random | LC_CTYPE=C tr -dc "[:lower:]" | head -c 6`
export uid_2=`cat /dev/random | LC_CTYPE=C tr -dc "[:lower:]" | head -c 6`

# Sumo Logic Access Configuration
export Section1aSumoDeployment=""
export Section1bSumoAccessID=""
export Section1cSumoAccessKey=""
export Section1dSumoOrganizationId=""
export Section1eRemoveSumoResourcesOnDeleteStack=true

export InstallAPP="No"
export CreateExplorerView="No"
export CreateMetricRule="No"
export CreateFER="No"
export UpdateSource="No"
export TagResources="No"
export CreateCollector="No"
export AutoEnableS3="No"
export CreateDeliveryChannel="No"
export CreateTrail="No"

if [[ "${InstallType}" == "nothing" ]]
then
    echo "Deploying nothing."
elif [[ "${InstallType}" == "installapp" ]]
then
    export InstallAPP="Yes"
    export FolderName="Sourabh Folder"
elif [[ "${InstallType}" == "installexplorerviews" ]]
then
    export CreateExplorerView="Yes"
    export ExplorerName="ExplorerNameMyNae"
    export ExplorerFields="account,${uid_1},${uid_2}"
elif [[ "${InstallType}" == "metricrule" ]]
then
    export CreateMetricRule="Yes"
    export MetricRuleName="MyMetricRule"
    export MatchExpression="account=${uid_1} ${uid_2}=*"
    export EntityRule="\$${uid_2}._1"
elif [[ "${InstallType}" == "fer" ]]
then
    export CreateFER="Yes"
    export FERName="FieldExtraction${uid_1}"
    export FERScope="account=${uid_1} namespace=${uid_2}"
    export FERExpression="json \"${uid_1}\""
elif [[ "${InstallType}" == "collector" ]]
then
    # It includes source updates for both AWS and HTTP custom resource.
    export CreateCollector="Yes"
elif [[ "${InstallType}" == "updatefields" ]]
then
    export UpdateSource="Yes"
elif [[ "${InstallType}" == "tagresources" ]]
then
    export TagResources="Yes"
elif [[ "${InstallType}" == "autoenable" ]]
then
    export AutoEnableS3="Yes"
elif [[ "${InstallType}" == "createchannel" ]]
then
    export CreateDeliveryChannel="Yes"
elif [[ "${InstallType}" == "createcloudtrail" ]]
then
    export CreateTrail="Yes"
else
    echo "No Valid Choice."
fi

# Stack Name
export stackName="${AppName}-${InstallType}"

aws cloudformation deploy --profile ${AWS_PROFILE} --template-file ./SampleTemplate.yaml --region ${AWS_REGION} \
--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --stack-name ${stackName} \
--parameter-overrides Section1aSumoDeployment="${Section1aSumoDeployment}" Section1bSumoAccessID="${Section1bSumoAccessID}" \
Section1cSumoAccessKey="${Section1cSumoAccessKey}" Section1dSumoOrganizationId="${Section1dSumoOrganizationId}" \
Section1eRemoveSumoResourcesOnDeleteStack="${Section1eRemoveSumoResourcesOnDeleteStack}" InstallAPP="${InstallAPP}" \
FolderName="${FolderName}" ExplorerName="${ExplorerName}" ExplorerFields="${ExplorerFields}" MetricRuleName="${MetricRuleName}" \
MatchExpression="${MatchExpression}" FERName="${FERName}" FERScope="${FERScope}" FERExpression="${FERExpression}" \
CreateMetricRule="${CreateMetricRule}" CreateFER="${CreateFER}" CreateExplorerView="${CreateExplorerView}" EntityRule="${EntityRule}" \
CreateCollector="${CreateCollector}" UpdateSource="${UpdateSource}" TagResources="${TagResources}" AutoEnableS3="${AutoEnableS3}" \
CreateDeliveryChannel="${CreateDeliveryChannel}" CreateTrail="${CreateTrail}"