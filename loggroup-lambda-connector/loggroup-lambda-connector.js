var AWS = require("aws-sdk");

function subscribeToLambda(lambdaLogGroupName, lambdaArn, errorHandler) {
    var cwl = new AWS.CloudWatchLogs({apiVersion: '2014-03-28'});
    var params = {
        destinationArn: lambdaArn,
        filterName: 'SumoLGLBDFilter',
        filterPattern: '',
        logGroupName: lambdaLogGroupName
    };
    // does it require permission
    cwl.putSubscriptionFilter(params, errorHandler);
}

function filterLogGroups(event, logGroupRegex) {
    logGroupRegex = new RegExp(logGroupRegex, "i");
    var logGroupName = event.detail.requestParameters.logGroupName;
    if (logGroupName.match(logGroupRegex) && event.detail.eventName === "CreateLogGroup") {
        return true;
    } else {
        return false;
    }
}

function processEvents(env, event, errorHandler) {

    var logGroupName = event.detail.requestParameters.logGroupName;
    if (filterLogGroups(event, env.LOG_GROUP_PATTERN)) {
        subscribeToLambda(logGroupName, env.LAMBDA_ARN, errorHandler);
        console.log("Subscribed: ", logGroupName, env.LAMBDA_ARN);
    } else {
        console.log("Unsubscribed: ", logGroupName, env.LAMBDA_ARN);
    }

}

exports.handler = function (event, context, callback) {
    processEvents(process.env, event, function (err, msg) {
        if (err) {
            console.log(err, msg);
            callback(err);
        } else {
            console.log("Success", msg);
            callback(null, "Success");
        }
    });

};
