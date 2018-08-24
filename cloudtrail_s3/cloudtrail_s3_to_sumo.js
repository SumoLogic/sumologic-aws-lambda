/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//                                        CloudTrail S3 bucket log to SumoLogic                                    //
//               https://github.com/SumoLogic/sumologic-aws-lambda                                                 //
//                                                                                                                 //
//        YOU MUST CREATE A SUMO LOGIC ENDPOINT CALLED SUMO_ENDPOINT AND PASTE IN ENVIRONMENTAL VARIABLES BELOW    //
//            https://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source             //
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// SumoLogic Endpoint to post logs
var SumoURL = process.env.SUMO_ENDPOINT;

var AWS = require('aws-sdk');
var s3 = new AWS.S3();
var https = require('https');
var zlib = require('zlib');
var url = require('url');

function s3LogsToSumo(bucket, objKey,context) {
    var urlObject = url.parse(SumoURL);
    var options = {
        'hostname': urlObject.hostname,
        'path': urlObject.pathname,
        'method': 'POST'
    };
    options.headers = {
        'X-Sumo-Name': objKey,
        'X-Sumo-Client': 'cloudtrail_s3-aws-lambda'
    };
    var req = https.request(options, function(res) {
                var body = '';
                console.log('Status:', res.statusCode);
                res.setEncoding('utf8');
                res.on('data', function(chunk) { body += chunk; });
                res.on('end', function() {
                    console.log('Successfully processed HTTPS response');
                    context.succeed();
                });
            });
    var finalData = '';

    if (objKey.match(/CloudTrail-Digest/)) {
        console.log("digest file are ignored");
        context.succeed();
    }

    var s3Stream = s3.getObject({Bucket: bucket, Key: objKey}).createReadStream();
    s3Stream.on('error', function() {
        console.log(
            'Error getting object "' + objKey + '" from bucket "' + bucket + '".  ' +
            'Make sure they exist and your bucket is in the same region as this function.');
        context.fail();
    });
   var gunzip = zlib.createGunzip();
    s3Stream.pipe(gunzip);
    gunzip.on('data',function(data) {
        finalData += data.toString();
    }).on('end',function(end){
        // READ THE UNZIPPED CloudTrail logs
        var records = JSON.parse(finalData);
        console.log(records.Records.length + " cloudtrail records in this file");
        for (var i = 0, len = records.Records.length; i < len; i++) {
            req.write(JSON.stringify(records.Records[i]) + '\n');
        }
        req.end();
    }).on('error',function(error) {
        context.fail(error);
    });
}

exports.handler = function(event, context) {
    //options.agent = new https.Agent(options);
    // Validate URL has been set
    var urlObject = url.parse(SumoURL);
    if (urlObject.protocol != 'https:' || urlObject.host === null || urlObject.path === null) {
        context.fail('Invalid SUMO_ENDPOINT environment variable: ' + SumoURL);
    }
    var bucket = event.Records[0].s3.bucket.name;
    var objKey = decodeURIComponent(event.Records[0].s3.object.key.replace(/\+/g, ' '));
    console.log('Bucket: '+bucket + ' ObjectKey: ' + objKey);
    s3LogsToSumo(bucket, objKey, context);
}
