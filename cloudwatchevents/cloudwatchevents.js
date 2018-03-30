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

var https = require('https');
var zlib = require('zlib');
var url = require('url');


function postToSumo(context, messages) {
    var messagesTotal = Object.keys(messages).length;
    var messagesSent = 0;
    var messageErrors = [];
    
    var urlObject = url.parse(SumoURL);
    var options = {
        'hostname': urlObject.hostname,
        'path': urlObject.pathname,
        'method': 'POST'
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


    Object.keys(messages).forEach(function (key, index) {
        var headerArray = key.split(':');
        options.headers = {
            'X-Sumo-Name': headerArray[0],
            'X-Sumo-Category': headerArray[1],
            'X-Sumo-Host': headerArray[2],
            'X-Sumo-Client': 'cloudwatchevents-aws-lambda'
        };

        var req = https.request(options, function (res) {
            res.setEncoding('utf8');
            res.on('data', function (chunk) {});
            res.on('end', function () {
                console.log("Got response code: "+ res.statusCode);
                if (res.statusCode == 200) {
                    messagesSent++;
                } else {
                    messageErrors.push('HTTP Return code ' + res.statusCode);
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
    
    // Used to hold chunks of messages to post to SumoLogic
    var messageList = {};

    // Validate URL has been set
    var urlObject = url.parse(SumoURL);
    if (urlObject.protocol != 'https:' || urlObject.host === null || urlObject.path === null) {
        context.fail('Invalid SUMO_ENDPOINT environment variable: ' + SumoURL);
    }
    
    //console.log(event);
    if ((event.source==="aws.guardduty") || (removeOuterFields)) {
        final_event =event.detail;
    } else {
        final_event = event;
    }   
    messageList[sourceNameOverride+':'+sourceCategoryOverride+':'+sourceHostOverride]=[final_event];
    postToSumo(context, messageList);
};
