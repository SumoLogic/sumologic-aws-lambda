var AWS = require("aws-sdk");
var processLogsHandler = require('./cloudwatchlogs_lambda').processLogs;

function receiveMessages(messageCount, sqs, env, callback) {
    var params = {
        QueueUrl: env.TASK_QUEUE_URL,
        MaxNumberOfMessages: messageCount
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

function initworkers(env, context) {
    var lambda = new AWS.Lambda({
      region: env.AWS_REGION
    });

    for (var i = 0; i < parseInt(env.NUM_OF_WORKERS); i++) {
        lambda.invoke({
            InvocationType: 'Event',
            FunctionName: context.functionName,
            Payload: '{"is_worker": "1"}'
        }, function(err, data) {
           if (err) {
               context.fail(err);
           } else {
               context.succeed('success');
           }
        });
    }
}
exports.consumeMessages = function (env, context, callback) {
    var sqs = new AWS.SQS({region: env.AWS_REGION});

    receiveMessages(10, sqs, env, function (err, messages) {

        if (err) {
            callback(err);
        } else if (messages && messages.length > 0) {
            env['SUMO_CLIENT_HEADER'] = 'dlq-cwl-lambda';
            var fail_cnt = 0;
            console.log("Messages Received", messages.length);
            for (var i = 0; i < messages.length; i++) {
                try {
                    var logdata = JSON.parse(messages[i].Body).awslogs.data;
                    processLogsHandler(env, context, logdata);
                    deleteMessage(sqs, env, messages[i].ReceiptHandle, callback);
                } catch(err) {
                    fail_cnt += 1;
                }
            }
            if (fail_cnt == 0 && (parseInt(env.is_worker) === 0)) {
                initworkers(env, context);
            }
            callback(null, fail_cnt + ' success');
        } else {
            callback(null, 'success');
        }
    });
};
exports.AWS = AWS;

exports.handler = function (event, context, callback) {

    var env = process.env;
    env['is_worker'] = event.is_worker || 0;
    exports.consumeMessages(env, context, callback);
};

