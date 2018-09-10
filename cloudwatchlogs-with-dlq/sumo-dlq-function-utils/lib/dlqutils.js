var AWS = require("aws-sdk");

function Messages(env) {
    this.sqs = new AWS.SQS({region: env.AWS_REGION});
    this.env = env;
}

Messages.prototype.receiveMessages = function (messageCount, callback) {
    var params = {
        QueueUrl: this.env.TASK_QUEUE_URL,
        MaxNumberOfMessages: messageCount
    };
    this.sqs.receiveMessage(params, callback);
};

Messages.prototype.deleteMessage = function (receiptHandle, callback) {
    this.sqs.deleteMessage({
        ReceiptHandle: receiptHandle,
        QueueUrl: this.env.TASK_QUEUE_URL
    }, callback);
};

function invokeLambdas(awsRegion, numOfWorkers, functionName, payload, context) {

    for (var i = 0; i < numOfWorkers; i++) {
        var lambda = new AWS.Lambda({
          region: awsRegion
        });
        lambda.invoke({
            InvocationType: 'Event',
            FunctionName: functionName,
            Payload: payload
        }, function(err, data) {
           if (err) {
               context.fail(err);
           } else {
               context.succeed('success');
           }
        });
    }
}

module.exports = {
    Messages: Messages,
    invokeLambdas: invokeLambdas
};
