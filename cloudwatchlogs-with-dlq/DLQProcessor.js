var AWS = require("aws-sdk");
var processLogsHandler = require('./cloudwatchlogs_lambda').processLogs;
var getEndpointURL = require('./cloudwatchlogs_lambda').getEndpointURL;
var DLQUtils = require("./sumo-dlq-function-utils").DLQUtils;
var Messages = DLQUtils.Messages;
var invokeLambdas = DLQUtils.invokeLambdas;

exports.consumeMessages = async function (env, context, callback) {
    var sqs = new AWS.SQS({region: env.AWS_REGION});
    var MessagesObj = new Messages(env);
    env.SUMO_CLIENT_HEADER="dlq-aws-lambda";
    if (!env.SUMO_ENDPOINT) {
        let SUMO_ENDPOINT = await getEndpointURL();
        if (SUMO_ENDPOINT instanceof Error) {
            console.log("Error in getEndpointURL: ", SUMO_ENDPOINT);
            callback(SUMO_ENDPOINT, null);
            return;
        }
        env.SUMO_ENDPOINT = SUMO_ENDPOINT;
    } else {
        console.log("consumeMessages: Getting SUMO_ENDPOINT from env");
    }
    MessagesObj.receiveMessages(10, function (err, data) {
        var messages = (data)? data.Messages: null;
        if (err) {
            callback(err);
        } else if (messages && messages.length > 0) {
            var fail_cnt = 0, msgCount = 0;
            console.log("Messages Received", messages.length);
            for (var i = 0; i < messages.length; i++) {
                (function(idx) {
                    var payload = JSON.parse(messages[idx].Body);
                    var receiptHandle = messages[idx].ReceiptHandle;
                    if (!(payload.awslogs && payload.awslogs.data)) {
                        console.log("Message does not contain awslogs or awslogs.data attributes", payload);
                        //deleting msg in DLQ after injesting in sumo
                        MessagesObj.deleteMessage(receiptHandle, function (err, data) {
                            if (err) console.log(err, err.stack);
                        });
                        return;
                    }
                    var logdata = payload.awslogs.data;
                    processLogsHandler(env, logdata, function (err, msg) {
                        msgCount++;
                        if (err) {
                            console.log(err, msg);
                            fail_cnt++;
                        } else {
                            //deleting msg in DLQ after injesting in sumo
                            MessagesObj.deleteMessage(receiptHandle, function (err, data) {
                                if (err) console.log(err, err.stack);
                            });
                        }
                        if (msgCount == messages.length) {
                            if (fail_cnt == 0 && (parseInt(env.is_worker) === 0)) {
                                invokeLambdas(env.AWS_REGION, parseInt(env.NUM_OF_WORKERS),
                                              context.functionName, '{"is_worker": "1"}', context);
                            }
                            callback(null, (messages.length-fail_cnt) + ' success');
                        }
                    });
                })(i);
            }

        } else {
            callback(null, 'success');
        }
    });
};

exports.handler = function (event, context, callback) {

    var env = Object.assign({}, process.env);
    env['is_worker'] = event.is_worker || 0;
    exports.consumeMessages(env, context, callback);
};

