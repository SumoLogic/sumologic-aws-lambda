===========================================
Kinesis to Sumo Logic
===========================================

Files 
-----
*	*node.js/k2sl_lambda.js*:  node.js function to read messages from a Kinesis stream and posts them to a Sumo Logic hosted HTTP collector.

## Lambda configuration

There are no module dependencies for this code, so you can paste it into the
lambda console directly. Note you must set the collector host and the
path that includes your secret key in options for this to work.

For the Sumo collector configuration, do not enable multiline processing or
one message per request -- the idea is to send as many messages in one request
as possible to Sumo and let Sumo break them apart as needed.

In the AWS console, use a code entry type of 'Edit code inline' and paste in the
code (doublecheck the hostname and path as per your collector setup).

In configuration specify index.handler as the Handler. Specify a Role that has
sufficient privileges to read from the kinesis stream, invoke a lambda
function, and write cloud watch logs. I tested with this policy, which is
too loose for production.

<pre>
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "kinesis:DescribeStream",
        "kinesis:ListStreams",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
</pre>

For the Event Source, pick the stream containing the data you want to send to Sumo.
