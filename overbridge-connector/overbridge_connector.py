import json
import time
import boto3


def lambda_handler(event, context):

    account_id = "956882708938"
    region_name = 'us-east-1'
    overbridge = boto3.client('overbridge', region_name=region_name)
    findings = [{
        "SchemaVersion": "2018-10-08",
        "ProductArn": "arn:aws:overbridge:%s:%s:provider:private/default" % (region_name, account_id),
        "AwsAccountId": account_id,
        "Id": "test_sdk_123456789012_12345",
        "GeneratorId": "TestDetector",
        "Types": [],
        "CreatedAt": "2017-03-22T13:22:13.933Z",
        "UpdatedAt": "2017-03-22T13:22:13.933Z",
        "Severity": {
            "Product": 10.0,
            "Normalized": 100
        },
        "Resources": [{
            "Type": "AWS::EC2::Instance",
            "Id": "arn:aws:ec2:us-east-1:123456789012:instance:i-123abc"
        }],
        "ExternalId": "8576f70be0c7e3a70088c00e13569f358576f70be0c7e3a70088c00e13569f358576f70be0c7e3a70088c00e13569f358576f70be0c7e3a70088c00e13569f35"
    }]
    import_response = overbridge.import_findings(
        Findings=findings
    )

    print import_response


    print "Sleeping for 10 seconds. Findings may take several seconds to show up in Overbridge."
    time.sleep(10)


    filters = {
        "ProductArn": [{
            "Value": "arn:aws:overbridge:%s:%s:provider:private/default" % (region_name, account_id),
            "Comparison": "EQUALS"
        }],
        "Id": [{
            "Value": "test_sdk_123456789012_12345",
            "Comparison": "EQUALS"
        }]
    }
    get_findings_response = overbridge.get_findings(
        Filters=filters
    )

    print get_findings_response

    return {
        "statusCode": 200,
        "body": "Success"
    }
if __name__ == '__main__':
    lambda_handler(None, None)
