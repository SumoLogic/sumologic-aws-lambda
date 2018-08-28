# Kinesis Firehose Processor
This function is used for transforming streaming data from kinesis firehose before it sents to destination.
Other use cases might include normalizing data produced by different producers, adding metadata to the record, or converting incoming data to a format suitable for the destination. In Sumo Logic's perspective it solves the problem of adding delimters between consecutive records so that they can be easily processed by Sumo Logic's Hosted Collector configured with [S3 source](https://help.sumologic.com/Send-Data/Sources/02Sources-for-Hosted-Collectors/Amazon_Web_Services/AWS_S3_Source).

# How it works
When you enable Firehose data transformation, Firehose buffers incoming data and invokes the specified Lambda function with each buffered batch asynchronously. The transformed data is sent from Lambda to Firehose for buffering and then delivered to the destination.

### Creating Stack in AWS Cloudformation
you can create the stack by using [aws-cli](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-cli-creating-stack.html) or directly from aws console using webbrowser and uploading kinesisfirehose-lambda-sam.yaml. For more details checkout it's [documentation](https://help.sumologic.com/?cid=39393)
Sumo Logic provides a Cloudformation [template](https://s3.amazonaws.com/appdev-cloudformation-templates/kinesisfirehose-lambda-cft.json) for creating the lambda function download and use it for creating the stack.

### Setting up the Lambda Function
Below instructions assumes that the delivery stream already exists.One can also configure the lambda at the time of delivery stream creation. Refer [Setting up Delivery Stream](https://docs.aws.amazon.com/firehose/latest/dev/basic-create.html)
* Go to https://console.aws.amazon.com/firehose/home
* Click on your delivery stream
* In Details Tab, click on edit
* In the edit window, Under Transform source records with AWS Lambda section enable the Source record transformation option. Now a bunch of options will be visible.
* In Lambda function select the function(starting with SumoKFLambdaProcessor) created by Cloudformation template.
* (Optional) you can set buffer size(lambda is invoked with this buffered batch) and buffer interval.
* Now scroll up and click on create new or update button beside IAM Role.
* In the new window click allow to give lambda invoke permission to Amazon Kinesis Firehose.
* Now click on Save

### Testing your Lambda Function
* Go to https://console.aws.amazon.com/firehose/home
* Click on your delivery stream
* Expand the Test with demo data section.
* Click on Start sending demo data. After few minutes you can see transformed data in your configured S3 bucket destination.
* You can view logs of lambda function in AWS Cloudwatch (LogGroup name beginning with /aws/lambda/SumoKFLambdaProcessor)

### For Developers

Installing Dependencies
```
  npm install
```

Building zip file
```
  npm run build
```
Upload the generated kinesisfirehose-processor.zip in S3 bucket(don't forget to change bucket name and key in cloudformation template)

