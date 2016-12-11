///////////////////////////////////////////////////////////////////////////////////////////////////////////
// Remember to change the hostname and path to match your collection API and specific HTTP-source endpoint
// See more at: https://help.sumologic.com/APIs/01Collector_Management_API
///////////////////////////////////////////////////////////////////////////////////////////////////////////
var sumoEndpoint = 'https://collectors.sumologic.com/receiver/v1/http/<XXX>';

// The following parameters can be specified to override the sourceCategoryOverride, sourceHostOverride and sourceNameOverride metadata fields within SumoLogic.
// Not these can also be overridden via json within the message payload. See the README for more information.
var sourceCategoryOverride = null;  // If null sourceCategoryOverride will not be overridden
var sourceHostOverride = null;      // If null sourceHostOverride will not be set to the name of the logGroup
var sourceNameOverride = null;      // If null sourceNameOverride will not be set to the name of the logStream

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


function sumoMetaKey(awslogsData, message) {
    var sourceCategory = '';
    var sourceName = '';
    var sourceHost = '';
    
    if (sourceCategoryOverride !== null) {
        sourceCategory = sourceCategoryOverride;
    }
    
    if (sourceHostOverride !== null) {
        sourceHost = sourceHostOverride;
    } else {
        sourceHost = awslogsData.logGroup;
    }
    
    if (sourceNameOverride !== null) {
        sourceName = sourceNameOverride;
    } else {
        sourceName = awslogsData.logStream;
    }
    
    // Ability to override metadata within the message
    // Useful within Lambda function console.log to dynamically set metadata fields within SumoLogic.
    if (message.hasOwnProperty('_sumo_metadata')) {
        var metadataOverride = log._sumo_metadata;
        if (metadataOverride.category) {
            sourceCategory = metadataOverride.category;
        }
        if (metadataOverride.host) {
            sourceHost = metadataOverride.host;
        }
        if (metadataOverride.source) {
            sourceName = metadataOverride.source;
        }
        delete log._sumo_metadata;
    }
    return sourceName + ':' + sourceCategory + ':' + sourceHost;
    
}

function postToSumo(context, messages) {
    var messagesTotal = Object.keys(messages).length;
    var messagesSent = 0;
    var messageErrors = [];
    
    var urlObject = url.parse(sumoEndpoint);
    var options = {
        'hostname': urlObject.hostname,
        'path': urlObject.pathname,
        'method': 'POST'
    };
    
    var finalizeContext = function () {
        var total = messagesSent + messageErrors.length;
        if (total == messagesTotal) {
            var message = 'messagesSent: ' + messagesSent + ' messagesErrors: ' + messageErrors.length;
            if (messageErrors.length > 0) {
                context.fail(message + ' errors: ' + messageErrors);
            } else {
                context.succeed(message);
            }
            console.log(message);
        }
    };
    
    
    Object.keys(messages).forEach(function (key, index) {
        var headerArray = key.split(':');
        options.headers = {
            'X-Sumo-Category': headerArray[0],
            'X-Sumo-Name': headerArray[0],
            'X-Sumo-Host': headerArray[0]
        };
        
        var req = https.request(options, function (res) {
            res.on('end', function () {
                if (res.statusCode == 200) {
                    messagesSent++;
                } else {
                    errors.push('HTTP Return code ' + res.statusCode);
                }
                finalizeContext();
            });
        });
        
        req.on('error', function (e) {
            messageErrors.push(e.message);
            finalizeContext();
        });
        
        for (var i = 0; i < messages[key].length; i++) {
            req.write(JSON.stringify(messages[key][i]) + '\n');
        }
        req.end();
    });
}


exports.handler = function (event, context) {
    
    var messages_list = {};
    
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
        
        var lastRequestID = null;
        
        console.log('total events: ' + awslogsData.logEvents.length);
        
        // Chunk log events before posting to SumoLogic
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
                log.message.trim();
            }
            
            // delete id as it's not very useful
            delete log.id;
            
            if (includeLogInfo) {
                log.logStream = awslogsData.logStream;
                log.logGroup = awslogsData.logGroup;
            }
            
            if (lastRequestID) {
                log.requestID = lastRequestID;
            }
            
            var metadataKey = sumoMetaKey(awslogsData, log.message);
            
            if (metadataKey in messages_list) {
                messages_list[metadataKey].push(log);
            } else {
                messages_list[metadataKey] = [log];
            }
        });
        
        // Push messages to Sumo
        postToSumo(context, messages_list);
        
    });
};
