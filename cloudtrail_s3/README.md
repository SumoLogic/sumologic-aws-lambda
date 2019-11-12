# Warning: This Lambda Function has been deprecated
We recommend using [S3 Event Notifications Integration](https://help.sumologic.com/Send-Data/Sources/02Sources-for-Hosted-Collectors/Amazon_Web_Services/AWS_S3_Source#S3_Event_Notifications_Integration),


Cloudtrail S3 to Sumo Logic
===========================================

Files
-----
*	*cloudtrail_s3_to_sumo.js*:  node.js function to read files from an S3 bucket to a Sumo Logic hosted HTTP collector. Files in the source bucket are gzipped. The function receives S3 notifications on new files uploaded to the source S3 bucket, then reads these files, unzips them, and breakdown the records before finally sends the data to the target Sumo endpoint.

## Lambda Setup
For the Sumo collector configuration, do not enable multiline processing or
one message per request -- Additionally, the timeformat should be adjusted to ensure the eventTime is the messageTime.
In the source Timestamp Format section, add a format <b>yyyy-MM-dd'T'HH:mm:ss'Z'</b> with Timestamp locator <b>eventTime\":\"(.*)?\"</b>
.

In the AWS console, use a code entry type of 'Edit code inline' and paste in the
code. In the Environment variable section, set the following Key to the URL provided from Sumo collector configuration.
<b>SUMO_ENDPOINT</b>

In configuration specify index.handler as the Handler. Specify a Role that has
sufficient privileges to read from the *source* bucket, and invoke a lambda
function. The code provided is tested with node runtime 4.3, 6.10, 8.10 and 10.x Memory setting at 128MB, Timeout 10s.

Set trigger to S3 bucket create-all events.

One can use the AWSLambdaBasicExecution and the AWSS3ReadOnlyAccess role, although it is *strongly* recommended to customize them to restrict to relevant resources in production:

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

This function should just work. If you are going to "test" this function under the AWS console, make sure you are feeding a "good" S3 CreateObject Event sample message. The default "hello world" event sample will error out.

Note on elapsed time: This value really depended on when did the event was written into the S3 file (file name contains the file creation time) and when did that S3:CreateObject was fired. To analyze the elapsed time, use the example query below.

_sourceCategory="global/aws/cloudtrail" | _receipttime-_messagetime as delta | delta/1000/60 as delta_min | timeslice 1m | avg(delta_min), max(delta_min), min(delta_min) by _timeslice

KNOWN ISSUE:
Occassionally, the function will fail with either TypeError or Socket Error. AWS has built-in retries to launch the function again with the same parameters (bucket/filename). There shouldn't be any data loss, but the function log will show those errors. Also, using Sumo to log this Lambda run is highly recommended.
