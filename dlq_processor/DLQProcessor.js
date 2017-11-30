var AWS = require("aws-sdk");
var processLogsHandler = require('./cloudwatchlogs_lambda').processLogs;

function receiveMessages(sqs, env, callback) {
    var params = {
        QueueUrl: env.TASK_QUEUE_URL,
        MaxNumberOfMessages: 1
    };
    sqs.receiveMessage(params, function (err, data) {
        if (err) {
            console.error(err, err.stack);
            callback(err);
        } else {
            callback(null, data.Messages);
        }
    });
}

function deleteMessage(sqs, env, receiptHandle, cb) {
    sqs.deleteMessage({
        ReceiptHandle: receiptHandle,
        QueueUrl: env.TASK_QUEUE_URL
    }, cb);
}

exports.consumeMessages = function (env, context, callback) {
    var sqs = new AWS.SQS({region: env.AWS_REGION});
    receiveMessages(sqs, env, function (err, messages) {
        if (err) {
            callback(err);
        } else if (messages && messages.length > 0) {
            console.log("Messages Recieved", messages.length);
            // console.log("Message Body", messages[0].Body);
            // console.log("Message receiptHandle", messages[0].ReceiptHandle);
            try {
                var logdata = JSON.parse(messages[0].Body).awslogs.data;
                processLogsHandler(env, context, logdata);
                deleteMessage(sqs, env, messages[0].ReceiptHandle, callback);
            } catch (e) {
                callback(e);
            }
        } else {
            callback(null, 'success');
        }
    });
};
exports.AWS = AWS;

exports.handler = function (event, context, callback) {
    exports.consumeMessages(process.env, context, callback);
};

