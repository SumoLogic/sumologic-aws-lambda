#!/bin/sh

echo "Start S3 upload Script....."

bucket_name=app-json-store
match_case="AWS"

yourfilenames=`ls ../json/*.json`
for app_file in ${yourfilenames}
do
	if [[ "${app_file}" == *"${match_case}"* ]]; then
		echo "File Name is "${app_file}
    	aws s3 cp ${app_file} s3://${bucket_name}/ --acl public-read
    fi
done

echo "End S3 upload Script....."