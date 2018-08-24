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
var consoleFormatRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z\s(\w+?-\w+?-\w+?-\w+?-\w+)\s/;

// Used to extract RequestID
var requestIdRegex = /(?:RequestId:|Z)\s+([\w\d\-]+)/;
var stream = require('stream');
var zlib = require('zlib');
var url = require('url');
var generateHeaders = require('./sumo-dlq-function-utils').generateHeaders;
var SumoLogsClient = require('./sumo-dlq-function-utils').SumoLogsClient;

function sumoMetaKey(headerObj) {
    return headerObj['X-Sumo-Name'] + ':' + headerObj['X-Sumo-Category'] + ':' + headerObj['X-Sumo-Host'];
}

function getConfig(env, errorHandler) {
    var config = {
        // SumoLogic Endpoint to post logs
        "SumoURL": env.SUMO_ENDPOINT,

        // The following parameters override the sourceCategory, sourceHost and sourceName metadata fields within SumoLogic.
        // Not these can also be overridden via json within the message payload. See the README for more information.
        "sourceCategoryOverride": ("SOURCE_CATEGORY_OVERRIDE" in env) ?  env.SOURCE_CATEGORY_OVERRIDE: '',  // If none sourceCategoryOverride will not be overridden
        "sourceHostOverride": ("SOURCE_HOST_OVERRIDE" in env) ? env.SOURCE_HOST_OVERRIDE : '',          // If none sourceHostOverride will not be set to the name of the logGroup
        "sourceNameOverride": ("SOURCE_NAME_OVERRIDE" in env) ? env.SOURCE_NAME_OVERRIDE : '',          // If none sourceNameOverride will not be set to the name of the logStream
        "SUMO_CLIENT_HEADER": env.SUMO_CLIENT_HEADER || 'cwl-aws-lambda',
        // CloudWatch logs encoding
        "encoding": env.ENCODING || 'utf-8'  // default is utf-8
    };

    // Validate URL has been set
    var urlObject = url.parse(config.SumoURL);
    if (urlObject.protocol !== 'https:' || urlObject.host === null || urlObject.path === null) {
        errorHandler(new Error('Invalid SUMO_ENDPOINT environment variable: ' + config.SumoURL), 'Error in SumoURL');
    }

    return config;
}


exports.processLogs = function (env, eventAwslogsData, errorHandler) {

    var config = getConfig(env, errorHandler);
    var SumoLogsClientObj = new SumoLogsClient(config);

    // Used to hold chunks of messages to post to SumoLogic
    var messageList = {};

    var zippedInput = new Buffer(eventAwslogsData, 'base64');
    var cb = function (e, buffer) {
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
                log.message = log.message.trim();
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
            var headers = {
                'X-Sumo-Name': headerArray[0],
                'X-Sumo-Category': headerArray[1],
                'X-Sumo-Host': headerArray[2],
                'X-Sumo-Client': config.SUMO_CLIENT_HEADER
            };
            // removing headers with 'none'
            for (var key in headers) {
                if (!headers[key] || (headers[key].toLowerCase() === 'none'))
                    delete headers[key]
            }
            options.headers = headers
        });
    };
    var uncompressed_bytes = [];
    var gunzip = zlib.createGunzip();
    gunzip.on('data', function (data) {
        uncompressed_bytes.push(data.toString());
    }).on("end", function () {
        cb(null, uncompressed_bytes.join(""));
    }).on("error", function (e) {
        cb(e);
    });
    var bufferStream = new stream.PassThrough();
    bufferStream.end(zippedInput);
    bufferStream.pipe(gunzip);
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
