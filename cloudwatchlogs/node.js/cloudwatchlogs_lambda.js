///////////////////////////////////////////////////////////////////////////////////////////////////////////
// Remember to change the hostname and path to match your collection API and specific HTTP-source endpoint
// See more at: https://help.sumologic.com/APIs/01Collector_Management_API
///////////////////////////////////////////////////////////////////////////////////////////////////////////
var sumoEndpoint = 'https://collectors.sumologic.com/receiver/v1/http/<XXX>';
 
// Format used to parse out log formats
// Example: 2016-11-10T23:11:54.523Z	108af3bb-a79b-11e6-8bd7-91c363cc05d9    some message
var consoleFormatRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z\t(\w+?-\w+?-\w+?-\w+?-\w+)\t(.*)/;

var https = require('https');
var zlib = require('zlib');
var url = require('url');

exports.handler = function (event, context) {
    var urlObject = url.parse(sumoEndpoint);
    
    var options = {
        'hostname': urlObject.hostname,
        'path': urlObject.pathname,
        'method': 'POST'
    };
    
    var zippedInput = new Buffer(event.awslogs.data, 'base64');
    
    zlib.gunzip(zippedInput, function (e, buffer) {
        if (e) {
            context.fail(e);
        }
        
        var awslogsData = JSON.parse(buffer.toString('ascii'));
        
        if (awslogsData.messageType === "CONTROL_MESSAGE") {
            console.log("Control message");
            context.succeed("Success");
        }
        
        var requestsSent = 0;
        var requestsFailed = 0;
        var finalizeContext = function () {
            var tot = requestsSent + requestsFailed;
            if (tot == awslogsData.logEvents.length) {
                if (requestsFailed > 0) {
                    context.fail(requestsFailed + " / " + tot + " events failed");
                } else {
                    context.succeed(requestsSent + " requests sent");
                }
            }
        };
        
        // Used to extract RequestID
        var requestIdRegex = /(?:RequestId:|Z)\s+([\w\d\-]+)/;
        var lastRequestID = null;

        awslogsData.logEvents.forEach(function (val, idx, arr) {
            options.headers = {
                'X-Sumo-Name': awslogsData.logStream,
                'X-Sumo-Host': awslogsData.logGroup
            };

            var req = https.request(options, function (res) {
                var body = '';
                console.log('Status:', res.statusCode);
                res.setEncoding('utf8');
                res.on('data', function (chunk) {
                    body += chunk;
                });
                res.on('end', function () {
                    console.log('Successfully processed HTTPS response');
                    requestsSent++;
                    finalizeContext();
                });
            });
            
            req.on('error', function (e) {
                console.log(e.message);
                requestsFailed++;
                finalizeContext();
            });
            
			// Remove trailing \n
			val.message = val.message.replace(/\n$/, '');
			
            // Try extract requestID
            var requestId = requestIdRegex.exec(val.message);
            if (requestId !== null) {
                lastRequestID = requestId[1];
            }
            
            // Attempt to detect console log and auto extract requestID and message
            var consoleLog = consoleFormatRegex.exec(val.message);
            if (consoleLog !== null) {
                lastRequestID = consoleLog[1];
                val.message = consoleLog[2].trim();
            }

            // Auto detect if message is json
            try {
                val.message = JSON.parse(val.message);
            } catch (err) {
                // Do nothing, leave as text
                val.message.trim()
            }
			
            // delete id as it's not very useful
            delete val.id;

            val.requestID = lastRequestID;
            req.end(JSON.stringify(val));
        });
        
    });
};
