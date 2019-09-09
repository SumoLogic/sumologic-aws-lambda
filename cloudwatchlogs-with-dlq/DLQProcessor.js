var AWS = require("aws-sdk");
var processLogsHandler = require('./cloudwatchlogs_lambda').processLogs;
var DLQUtils = require("./sumo-dlq-function-utils").DLQUtils;
var Messages = DLQUtils.Messages;
var invokeLambdas = DLQUtils.invokeLambdas;

exports.consumeMessages = function (env, context, callback) {
    var sqs = new AWS.SQS({region: env.AWS_REGION});
    var MessagesObj = new Messages(env);
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
                    env.SUMO_CLIENT_HEADER="dlq-aws-lambda";
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

    var env = process.env;
    env['is_worker'] = event.is_worker || 0;
    exports.consumeMessages(env, context, callback);
};

