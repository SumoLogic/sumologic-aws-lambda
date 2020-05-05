//////////////////////////////////////////////////////////////////////////////////
// CloudWatch Logs to SumoLogic //
// https://github.com/SumoLogic/sumologic-aws-lambda/tree/master/cloudwatchlogs //
//////////////////////////////////////////////////////////////////////////////////

// SumoLogic Endpoint to post logs
var SumoURL = process.env.SUMO_ENDPOINT;

// The following parameters override the sourceCategoryOverride, sourceHostOverride and sourceNameOverride metadata fields within SumoLogic.
// Not these can also be overridden via json within the message payload. See the README for more information.
var sourceCategoryOverride = process.env.SOURCE_CATEGORY_OVERRIDE || 'none'; // If none sourceCategoryOverride will not be overridden
var sourceHostOverride = process.env.SOURCE_HOST_OVERRIDE || 'none'; // If none sourceHostOverride will not be set to the name of the logGroup
var sourceNameOverride = process.env.SOURCE_NAME_OVERRIDE || 'none'; // If none sourceNameOverride will not be set to the name of the logStream

var retryInterval = process.env.RETRY_INTERVAL || 5000; // the interval in millisecs between retries
var numOfRetries = process.env.NUMBER_OF_RETRIES || 3; // the number of retries

// CloudWatch logs encoding
var encoding = process.env.ENCODING || 'utf-8'; // default is utf-8

// Include logStream and logGroup as json fields within the message. Required for SumoLogic AWS Lambda App
var includeLogInfo = true; // default is true

// Regex used to detect logs coming from lambda functions.
// The regex will parse out the requestID and strip the timestamp
// Example: 2016-11-10T23:11:54.523Z 108af3bb-a79b-11e6-8bd7-91c363cc05d9 some message
var consoleFormatRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z\s(\w+?-\w+?-\w+?-\w+?-\w+)\s(INFO|ERROR|WARN|DEBUG)?/;

// Used to extract RequestID
var requestIdRegex = /(?:RequestId:|Z)\s+([\w\d\-]+)/;

var https = require('https');
var zlib = require('zlib');
var url = require('url');

Promise.retryMax = function(fn,retry,interval,fnParams) {
    return fn.apply(this,fnParams).catch( err => {
        var waitTime = typeof interval === 'function' ? interval() : interval;
        console.log("Retries left " + (retry-1) + " delay(in ms) " + waitTime);
        return (retry>1? Promise.wait(waitTime).then(()=> Promise.retryMax(fn,retry-1,interval, fnParams)):Promise.reject(err));
    });
}

Promise.wait = function(delay) {
    return new Promise((fulfill,reject)=> {
        //console.log(Date.now());
        setTimeout(fulfill,delay||0);
    });
};

function exponentialBackoff(seed) {
    var count = 0;
    return function() {
        count++;
        return count*seed;
    }
}

function sumoMetaKey(awslogsData, message, data) {
    var sourceCategory = '';
    var sourceName = '';
    var sourceHost = '';

    if (sourceCategoryOverride !== null && sourceCategoryOverride !== '' && sourceCategoryOverride != 'none') {
        sourceCategory = sourceCategoryOverride;
    }

    if (sourceHostOverride !== null && sourceHostOverride !== '' && sourceHostOverride != 'none') {
        sourceHost = sourceHostOverride;
    } else {
        sourceHost = awslogsData.logGroup;
    }

    if (sourceNameOverride !== null && sourceNameOverride !== '' && sourceNameOverride != 'none') {
        sourceName = sourceNameOverride;
    } else {
        sourceName = awslogsData.logStream;
    }

    // Ability to override metadata within the message
    // Useful within Lambda function console.log to dynamically set metadata fields within SumoLogic.
    if (message.hasOwnProperty('_sumo_metadata')) {
        var metadataOverride = message._sumo_metadata;
        if (metadataOverride.category) {
            sourceCategory = metadataOverride.category;
        }
        if (metadataOverride.host) {
            sourceHost = metadataOverride.host;
        }
        if (metadataOverride.source) {
            sourceName = metadataOverride.source;
        }
        delete message._sumo_metadata;
    }
    return sourceName + ':' + sourceCategory + ':' + sourceHost;

}

function postToSumo(context, messages) {
    var messagesTotal = Object.keys(messages).length;
    var messagesSent = 0;
    var messageErrors = [];

    var urlObject = url.parse(SumoURL);
    var options = {
        'hostname': urlObject.hostname,
        'path': urlObject.pathname,
        'method': 'POST',
        'port': urlObject.port
    };

    var finalizeContext = function () {
        var total = messagesSent + messageErrors.length;
        if (total == messagesTotal) {
            console.log('messagesSent: ' + messagesSent + ' messagesErrors: ' + messageErrors.length);
            if (messageErrors.length > 0) {
                context.fail('errors: ' + messageErrors);
            } else {
                context.succeed();
            }
        }
    };

    function httpSend(options, headers, data) {
        return new Promise( (resolve,reject) => {
            var curOptions = options;
            curOptions.headers = headers;
            var req = https.request(curOptions, function (res) {
                var body = '';
                res.setEncoding('utf8');
                res.on('data', function (chunk) {
                    body += chunk; // don't really do anything with body
                });
                res.on('end', function () {
                    if (res.statusCode == 200) {
                        resolve(body);
                    } else {
                        reject({'error':'HTTP Return code ' + res.statusCode,'res':res});
                    }
                });
            });
            req.on('error', function (e) {
                reject({'error':e,'res':null});
            });
            for (var i = 0; i < data.length; i++) {
                req.write(JSON.stringify(data[i]) + '\n');
            }
            console.log("sending to Sumo...")
            req.end();
        });
    }
    Object.keys(messages).forEach(function (key, index) {
        var headerArray = key.split(':');
        var headers = {
            'X-Sumo-Name': headerArray[0],
            'X-Sumo-Category': headerArray[1],
            'X-Sumo-Host': headerArray[2],
            'X-Sumo-Client': 'kinesis-aws-lambda'
        };
        Promise.retryMax(httpSend, numOfRetries, retryInterval, [options, headers, messages[key]]).then((body)=> {
            messagesSent++;
            finalizeContext()
        }).catch((e) => {
            messageErrors.push(e.error);
            finalizeContext();
        });
    });
}

exports.handler = function (event, context) {

    // console.log(JSON.stringify(event));

    // Used to hold chunks of messages to post to SumoLogic
    var messageList = {};

    // Validate URL has been set
    var urlObject = url.parse(SumoURL);
    if (urlObject.protocol != 'https:' || urlObject.host === null || urlObject.path === null) {
        context.fail('Invalid SUMO_ENDPOINT environment variable: ' + SumoURL);
    }
    var numOfRecords = event.Records.length;
    event.Records.forEach(function(record, index) {
        var awslogsData = {};

        try {
            awslogsData = JSON.parse(zlib.gunzipSync(Buffer.from(record.kinesis.data, 'base64')).toString(encoding));
        } catch (e) {
            context.fail(e);
        }

        if (awslogsData.messageType === 'CONTROL_MESSAGE') {
            console.log('Control message');
            context.succeed('Success');
        }

        var lastRequestID = null;

        console.log('Log events: ' + awslogsData.logEvents.length);

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
                log.message = log.message.substring(consoleLog[0].length);
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

            if (metadataKey in messageList) {
                messageList[metadataKey].push(log);
            } else {
                messageList[metadataKey] = [log];
            }
        });
        // Push messages to Sumo
        if (index === numOfRecords-1) {
            postToSumo(context, messageList);
        }

    });
};

