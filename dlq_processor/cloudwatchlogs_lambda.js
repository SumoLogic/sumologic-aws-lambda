/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//                                        CloudWatch Logs to SumoLogic                                             //
//               https://github.com/SumoLogic/sumologic-aws-lambda/tree/master/cloudwatchlogs                      //
//                                                                                                                 //
//        YOU MUST CREATE A SUMO LOGIC ENDPOINT CALLED SUMO_ENDPOINT AND PASTE IN ENVIRONMENTAL VARIABLES BELOW    //
//            https://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source             //
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Include logStream and logGroup as json fields within the message. Required for SumoLogic AWS Lambda App
var includeLogInfo = true;  // default is true

// Regex used to detect logs coming from lambda functions.
// The regex will parse out the requestID and strip the timestamp
// Example: 2016-11-10T23:11:54.523Z	108af3bb-a79b-11e6-8bd7-91c363cc05d9    some message
var consoleFormatRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z\t(\w+?-\w+?-\w+?-\w+?-\w+)\t/;

// Used to extract RequestID
var requestIdRegex = /(?:RequestId:|Z)\s+([\w\d\-]+)/;

var zlib = require('zlib');
var url = require('url');
var generateHeaders = require('./sumo-dlq-function-utils').generateHeaders;
var SumoLogsClient = require('./sumo-dlq-function-utils').SumoLogsClient;

function sumoMetaKey(headerObj) {
    return headerObj['X-Sumo-Name'] + ':' + headerObj['X-Sumo-Category'] + ':' + headerObj['X-Sumo-Host'];
}

function getConfig(env) {
    var config = {
        // SumoLogic Endpoint to post logs
        "SumoURL": env.SUMO_ENDPOINT,

        // The following parameters override the sourceCategoryOverride, sourceHostOverride and sourceNameOverride metadata fields within SumoLogic.
        // Not these can also be overridden via json within the message payload. See the README for more information.
        "sourceCategoryOverride": env.SOURCE_CATEGORY_OVERRIDE || 'none',  // If none sourceCategoryOverride will not be overridden
        "sourceHostOverride": env.SOURCE_HOST_OVERRIDE || 'none',          // If none sourceHostOverride will not be set to the name of the logGroup
        "sourceNameOverride": env.SOURCE_NAME_OVERRIDE || 'none',          // If none sourceNameOverride will not be set to the name of the logStream
        "SUMO_CLIENT_HEADER": env.SUMO_CLIENT_HEADER || 'cwl-lambda',
        // CloudWatch logs encoding
        "encoding": env.ENCODING || 'utf-8'  // default is utf-8
    };
    return config;
}


exports.processLogs = function (env, eventAwslogsData, errorHandler) {

    var config = getConfig(env);
    var SumoLogsClientObj = new SumoLogsClient(config);

    // Used to hold chunks of messages to post to SumoLogic
    var messageList = {};

    // Validate URL has been set
    var urlObject = url.parse(config.SumoURL);
    if (urlObject.protocol !== 'https:' || urlObject.host === null || urlObject.path === null) {
        errorHandler('Invalid SUMO_ENDPOINT environment variable: ' + config.SumoURL, 'Error in SumoURL');
    }

    var zippedInput = new Buffer(eventAwslogsData, 'base64');

    zlib.gunzip(zippedInput, function (e, buffer) {
        if (e) {
            errorHandler(e, "Error in Unzipping");
            return;
        }

        var awslogsData = JSON.parse(buffer.toString(config.encoding));

        if (awslogsData.messageType === 'CONTROL_MESSAGE') {
            console.log('Control message');
            errorHandler(null, "Control Message");
            return;
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
            var headerObj = generateHeaders(config, log.message, awslogsData);
            var metadataKey = sumoMetaKey(headerObj);

            if (metadataKey in messageList) {
                messageList[metadataKey].push(log);
            } else {
                messageList[metadataKey] = [log];
            }
        });

        // Push messages to Sumo
        SumoLogsClientObj.postToSumo(messageList, errorHandler, function (options, messages, key) {
            var headerArray = key.split(':');
            options.headers = {
                'X-Sumo-Name': headerArray[0],
                'X-Sumo-Category': headerArray[1],
                'X-Sumo-Host': headerArray[2],
                'X-Sumo-Client': config.SUMO_CLIENT_HEADER
            };
        });
    });
};


exports.handler = function (event, context, callback) {
    exports.processLogs(process.env, event.awslogs.data, function (err, msg) {
        if (err) {
            console.log(err, msg);
            callback(err);
        } else {
            console.log(msg);
            callback(null, "Success");
        }
    });

};
