/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//                                        CloudWatch Events to SumoLogic                                           //
//               https://github.com/SumoLogic/sumologic-aws-lambda/tree/master/cloudwatchevents                    //
//                                                                                                                 //
//        YOU MUST CREATE A SUMO LOGIC ENDPOINT CALLED SUMO_ENDPOINT AND PASTE IN ENVIRONMENTAL VARIABLES BELOW    //
//            https://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source             //
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// SumoLogic Endpoint to post logs
var SumoURL = process.env.SUMO_ENDPOINT;

// For some beta AWS services, the default is to remove the outer fields of the received object since they are not useful.
// change this if necessary.
var removeOuterFields = false;

// The following parameters override the sourceCategoryOverride, sourceHostOverride and sourceNameOverride metadata fields within SumoLogic.
// Not these can also be overridden via json within the message payload. See the README for more information.
var sourceCategoryOverride = process.env.SOURCE_CATEGORY_OVERRIDE || '';  // If empty sourceCategoryOverride will not be overridden
var sourceHostOverride = process.env.SOURCE_HOST_OVERRIDE || '';          // If empty sourceHostOverride will not be set to the name of the logGroup
var sourceNameOverride = process.env.SOURCE_NAME_OVERRIDE || '';          // If empty sourceNameOverride will not be set to the name of the logStream

var retryInterval = process.env.RETRY_INTERVAL || 5000; // the interval in millisecs between retries
var numOfRetries = process.env.NUMBER_OF_RETRIES || 3;  // the number of retries

var https = require('https');
var zlib = require('zlib');

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

function httpSend(options, headers, data) {
    return new Promise( (resolve,reject) => {
        var curOptions = Object.assign({}, options);
        curOptions.headers = headers;
        var req = https.request(curOptions, function (res) {
            var body = '';
            res.setEncoding('utf8');
            res.on('data', function (chunk) {
                body += chunk;
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

async function postToSumo(messages) {
    var messagesSent = 0;
    var messageErrors = [];

    var urlObject = new URL(SumoURL);
    var options = {
        'hostname': urlObject.hostname,
        'path': urlObject.pathname + urlObject.search,
        'method': 'POST'
    };

    var keys = Object.keys(messages);
    for (var i = 0; i < keys.length; i++) {
        var key = keys[i];
        var headerArray = key.split(':');
        var headers = {
            'X-Sumo-Name': headerArray[0],
            'X-Sumo-Category': headerArray[1],
            'X-Sumo-Host': headerArray[2],
            'X-Sumo-Client': 'cloudwatchevents-aws-lambda'
        };
        try {
            await Promise.retryMax(httpSend, numOfRetries, retryInterval, [options, headers, messages[key]]);
            messagesSent++;
        } catch (e) {
            messageErrors.push(e.error);
        }
    }

    console.log('messagesSent: ' + messagesSent + ' messagesErrors: ' + messageErrors.length);
    if (messageErrors.length > 0) {
        throw new Error('errors: ' + messageErrors);
    }
    return "Success";
}

exports.handler = async function (event, context) {

    var messageList = {};
    var final_event;
    var urlObject;
    try {
        urlObject = new URL(SumoURL);
    } catch (e) {
        throw new Error('Invalid SUMO_ENDPOINT environment variable: ' + SumoURL);
    }
    if (urlObject.protocol !== 'https:' || !urlObject.hostname || !urlObject.pathname) {
        throw new Error('Invalid SUMO_ENDPOINT environment variable: ' + SumoURL);
    }

    if ((event.source==="aws.guardduty") || (removeOuterFields)) {
        final_event =event.detail;
    } else {
        final_event = event;
    }
    messageList[sourceNameOverride+':'+sourceCategoryOverride+':'+sourceHostOverride]=[final_event];
    return await postToSumo(messageList);
};
