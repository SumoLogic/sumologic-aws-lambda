# Warning: This Lambda Function has been deprecated
We recommend using [S3 Event Notifications Integration](https://help.sumologic.com/Send-Data/Sources/02Sources-for-Hosted-Collectors/Amazon_Web_Services/AWS_S3_Source#S3_Event_Notifications_Integration),

S3 to Sumo Logic
===========================================

Files 
-----
*	*node.js/s3.js*:  node.js function to read files from an S3 bucket to a Sumo Logic hosted HTTP collector. Files in the source bucket can be gzipped, or in cleartext, but should contain only texts. The function receives S3 notifications on new files uploaded to the source S3 bucket, then reads these files, or unzips them if the file names end with `gz`, and finally sends the data to the target Sumo endpoint.

## Lambda Setup 
For the Sumo collector configuration, do not enable multiline processing or
one message per request -- the idea is to send as many messages in one request
as possible to Sumo and let Sumo break them apart as needed.

In the AWS console, use a code entry type of 'Edit code inline' and paste in the
code (doublecheck the hostname and path as per your collector setup).

In configuration specify index.handler as the Handler. Specify a Role that has
sufficient privileges to read from the *source* bucket, and invoke a lambda
function. One can use the AWSLambdaBasicExecution and the AWSS3ReadOnlyAccess role, although it is *strongly* recommended to customize them to restrict to relevant resources in production:  

<pre>
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
</pre>

AND 

<pre>
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:Get*",
        "s3:List*"
      ],
      "Resource": "*"
    }
  ]
}
</pre>

Once the function is created, you can tie it to the source S3 bucket. From the S3 Management console, select the bucket, goto its Properties, select Events and add a Notification. From there, provide a name for the notification, select *ObjectCreated (All)* as the Events, and select *Lambda* as the *Send To* option. Finally, select the Lambda function created above and Save.


