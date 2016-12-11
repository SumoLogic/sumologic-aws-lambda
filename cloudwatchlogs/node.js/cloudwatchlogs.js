///////////////////////////////////////////////////////////////////////////////////////////////////////////
// Remember to change the hostname and path to match your collection API and specific HTTP-source endpoint
// See more at: https://help.sumologic.com/APIs/01Collector_Management_API
///////////////////////////////////////////////////////////////////////////////////////////////////////////
var sumoEndpoint = 'https://collectors.sumologic.com/receiver/v1/http/<XXX>';

// The following parameters can be specified to override the sourceCategory, sourceHost and sourceName metadata fields within SumoLogic.
// Not these can also be overridden via json within the message payload. See the README for more information.
var sourceCategory = null;  // If null sourceCategory will not be overridden
var sourceHost = null;      // If null sourceHost will not be set to the name of the logGroup
var sourceName = null;      // If null sourceName will not be set to the name of the logStream

// Include logStream and logGroup as json fields within the message. Required for SumoLogic AWS Lambda App
var includeLogInfo = true;  // default is true

// Regex used to detect logs coming from lambda functions.
// The regex will parse out the requestID and strip the timestamp
// Example: 2016-11-10T23:11:54.523Z	108af3bb-a79b-11e6-8bd7-91c363cc05d9    some message
var consoleFormatRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z\t(\w+?-\w+?-\w+?-\w+?-\w+)\t(.*)/;

// Used to extract RequestID
var requestIdRegex = /(?:RequestId:|Z)\s+([\w\d\-]+)/;

var https = require('https');
var zlib = require('zlib');
var url = require('url');


function sumoHeaders(awslogsData, message) {
    var headers = {};

    if (sourceCategory !== null) {
        headers['X-Sumo-Category'] = sourceCategory
    }
    
    if (sourceHost !== null) {
        headers['X-Sumo-Host'] = sourceHost
    } else {
        headers['X-Sumo-Host'] = awslogsData.logGroup
    }
    
    if (sourceName !== null) {
        headers['X-Sumo-Name'] = sourceName
    } else {
        headers['X-Sumo-Name'] = awslogsData.logStream
    }
    
    // Ability to override metadata within the message
    // Useful within Lambda function console.log to dynamically set metadata fields within SumoLogic.
    if (message.hasOwnProperty('_sumo_metadata')) {
        var metadataOverride = log._sumo_metadata;
        if (metadataOverride.category) {
            headers['X-Sumo-Category'] = metadataOverride.category;
        }
        if (metadataOverride.host) {
            headers['X-Sumo-Host'] = metadataOverride.host;
        }
        if (metadataOverride.source) {
            headers['X-Sumo-Name'] = metadataOverride.source;
        }
        delete log['_sumo_metadata']
    }
    return headers;
    
}


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
        
        var lastRequestID = null;
        
        awslogsData.logEvents.forEach(function (log, idx, arr) {

            // Remove any trailing \n
            log.message = log.message.replace(/\n$/, '');
            
            // Try extract requestID
            var requestId = requestIdRegex.exec(log.message);
            if (requestId !== null) {
                lastRequestID = requestId[1];
            }
            
            // Attempt to detect console log and auto extract requestID and message
            var consoleLog = consoleFormatRegex.exec(log.message);
            if (consoleLog !== null) {
                lastRequestID = consoleLog[1];
                log.message = consoleLog[2].trim();
            }
            
            // Auto detect if message is json
            try {
                log.message = JSON.parse(log.message);
            } catch (err) {
                // Do nothing, leave as text
                log.message.trim()
            }

            options.headers = sumoHeaders(awslogsData, log.message);

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
            
            // delete id as it's not very useful
            delete log.id;

            if (includeLogInfo) {
                log.logStream = awslogsData.logStream;
                log.logGroup = awslogsData.logGroup;
            }
            
            if (lastRequestID) {
                log.requestID = lastRequestID;
            }
            
            req.end(JSON.stringify(log));
        });
        
    });
};
