var AWS = require("aws-sdk");

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
  invokeLambdas: invokeLambdas
};
