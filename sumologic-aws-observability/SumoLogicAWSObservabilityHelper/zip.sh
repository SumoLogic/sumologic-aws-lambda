if [ -f SumoLogicAWSObservabilityHelper.zip ]; then
    rm SumoLogicAWSObservabilityHelper.zip
fi

if [ ! -f SumoLogicAWSObservabilityHelper.zip ]; then
    echo "creating zip file"
    mkdir python
    cd python
    pip install  crhelper -t .
    pip install requests -t .
    pip install boto3 -t .
    cp -v ../../../sumologic-app-utils/src/*.py .
    zip -r ../SumoLogicAWSObservabilityHelper.zip .
    cd ..
    rm -r python
fi

if [ -f SumoLogicCloudWatchEvents.zip ]; then
    rm SumoLogicCloudWatchEvents.zip
fi

if [ ! -f SumoLogicCloudWatchEvents.zip ]; then
    echo "creating zip file"
    mkdir python
    cd python
    pip install  crhelper -t .
    pip install requests -t .
    cp -v ../../../cloudwatchevents/src/*.js .
    zip -r ../SumoLogicCloudWatchEvents.zip .
    cd ..
    rm -r python
fi