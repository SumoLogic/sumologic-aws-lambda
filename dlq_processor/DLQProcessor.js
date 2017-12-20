var AWS = require("aws-sdk");
var processLogsHandler = require('./cloudwatchlogs_lambda').processLogs;
var DLQUtils = require("./sumo-dlq-function-utils");
var Messages = new DLQUtils.Messages(process.env);
var invokeLambdas = DLQUtils.invokeLambdas;

exports.consumeMessages = function (env, context, callback) {
    var sqs = new AWS.SQS({region: env.AWS_REGION});

    Messages.receiveMessages(10, function (err, messages) {

        if (err) {
            callback(err);
        } else if (messages && messages.length > 0) {
            var fail_cnt = 0, payload = '{"is_worker": "1"}';
            console.log("Messages Received", messages.length);
            for (var i = 0; i < messages.length; i++) {
                try {
                    var logdata = JSON.parse(messages[i].Body).awslogs.data;
                    processLogsHandler(env, context, logdata);
                    Messages.deleteMessage(messages[i].ReceiptHandle, callback);
                } catch(err) {
                    fail_cnt += 1;
                }
            }
            if (fail_cnt == 0 && (parseInt(env.is_worker) === 0)) {
                invokeLambdas(env.AWS_REGION, parseInt(env.NUM_OF_WORKERS),
                              context.functionName, payload, context);
            }
            callback(null, (messages.length-fail_cnt) + ' success');
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

