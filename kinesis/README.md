===========================================
Kinesis to Sumo Logic
===========================================
This function is invoked by AWS Lambda after it detects new records in Kinesis stream. The received collection of events are decompressed, transformed and send to Sumo Logic HTTP source endpoint.

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

## Lambda test event

Test event in order to test the Lambda

```json
{
  "Records": [
    {
      "kinesis": {
        "partitionKey": "partitionKey-03",
        "kinesisSchemaVersion": "1.0",
        "data": "H4sICL9JQFwAA2EA3VJNa4MwGL77K0rOdiRRY9KbrK7ssMuUXWYRN0MJqJEkbhTxvy+x4rreB2PvKeT5eJ8nZPQ2doD87LgCuw1AVwP8C9jI00HJoXf4fSOHOleVaK7QzChetbfy8ptbDnrLK222q6ce3vS7Er0RsnsQjeFKW/3rDM6EPddGdJXDwXx7XJQt17o68fzcc7dxn+RJ+ZRmWXJIryKlH7wzPy3H9TSTRO3kAWJRgCAhkDBCGA2CmFLIII5gzCgMsS0SBpgygqIQh5hRjFFE6LJqdTPC5jJV6x5pFmBCowhCeMNb0rvVYwG4S/liu9uWBdgVAN3BoAB+AQbN1WNtUWHOFrFcYwvPnGcpTQEmsBpP/q90ZP+/Ywz/VMfLP/cm7wsfrETjlgMAAA==",
        "sequenceNumber": "49545115243490985018280067714973144582180062593244200961",
        "approximateArrivalTimestamp": 1428537600
      },
      "eventSource": "aws:kinesis",
      "eventID": "shardId-000000000000:49545115243490985018280067714973144582180062593244200961",
      "invokeIdentityArn": "arn:aws:iam::EXAMPLE",
      "eventVersion": "1.0",
      "eventName": "aws:kinesis:record",
      "eventSourceARN": "arn:aws:kinesis:EXAMPLE",
      "awsRegion": "us-east-1"
    }
  ]
}
```


You should expect to see a response with an array of records. The Data attribute in an Kinesis record is Base64 encoded and compressed with the gzip format. You can examine the raw data from the command line using the following Unix commands:

`echo -n "<Content of Data>" | base64 -d | zcat`
  
The Base64 decoded and decompressed data is formatted as JSON with the following structure:

```json
{
    "owner": "111111111111",
    "logGroup": "CloudTrail",
    "logStream": "111111111111_CloudTrail_us-east-1",
    "subscriptionFilters": [
        "Destination"
    ],
    "messageType": "DATA_MESSAGE",
    "logEvents": [
        {
            "id": "31953106606966983378809025079804211143289615424298221568",
            "timestamp": 1432826855000,
            "message": "{\"eventVersion\":\"1.03\",\"userIdentity\":{\"type\":\"Root\"}"
        },
        {
            "id": "31953106606966983378809025079804211143289615424298221569",
            "timestamp": 1432826855000,
            "message": "{\"eventVersion\":\"1.03\",\"userIdentity\":{\"type\":\"Root\"}"
        },
        {
            "id": "31953106606966983378809025079804211143289615424298221570",
            "timestamp": 1432826855000,
            "message": "{\"eventVersion\":\"1.03\",\"userIdentity\":{\"type\":\"Root\"}"
        }
    ]
}
```
