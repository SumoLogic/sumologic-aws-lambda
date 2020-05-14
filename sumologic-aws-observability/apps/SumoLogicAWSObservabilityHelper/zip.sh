if [ -f SumoLogicAWSObservabilityHelper.zip ]; then
    rm SumoLogicAWSObservabilityHelper.zip
fi

if [ ! -f SumoLogicAWSObservabilityHelper.zip ]; then
    echo "creating zip file"
    mkdir python
    cd python
    pip install  crhelper -t .
    pip install requests -t .
    pip install retrying -t .
    cp -v ../../../sumologic-app-utils/src/*.py .
    zip -r ../SumoLogicAWSObservabilityHelper.zip .
    cd ..
    rm -r python
fi