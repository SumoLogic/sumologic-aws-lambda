var AWS = require("aws-sdk");
var processLogsHandler = require('./cloudwatchlogs_lambda').processLogs;
var Messages = require("./sumo-dlq-function-utils").Messages;
var AWSUtils = require("./sumo-dlq-function-utils").AWSUtils;
var invokeLambdas = AWSUtils.invokeLambdas;

exports.consumeMessages = function (env, context, callback) {
    var sqs = new AWS.SQS({region: env.AWS_REGION});
    var MessagesObj = new Messages(env);
    MessagesObj.receiveMessages(10, function (err, data) {
        var messages = (data)? data.Messages: null;
        if (err) {
            callback(err);
        } else if (messages && messages.length > 0) {
            var fail_cnt = 0, msgCount = 0, payload = '{"is_worker": "1"}';
            console.log("Messages Received", messages.length);
            for (var i = 0; i < messages.length; i++) {
                (function(idx) {
                    var logdata = JSON.parse(messages[idx].Body).awslogs.data;
                    var receiptHandle = messages[idx].ReceiptHandle;
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
                                              context.functionName, payload, context);
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

