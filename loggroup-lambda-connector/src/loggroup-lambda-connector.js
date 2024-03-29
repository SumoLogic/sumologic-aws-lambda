const { CloudWatchLogsClient, PutSubscriptionFilterCommand, DescribeLogGroupsCommand } = require("@aws-sdk/client-cloudwatch-logs");
const { LambdaClient, InvokeCommand } = require("@aws-sdk/client-lambda");

const cwl = new CloudWatchLogsClient();
const lambda = new LambdaClient({ apiVersion: '2015-03-31' }); // Update to the appropriate Lambda API version you require
const maxRetryCounter = 3;

async function createSubscriptionFilter(lambdaLogGroupName, destinationArn, roleArn) {
    var params={}; 
    if (destinationArn.startsWith("arn:aws:lambda")) {
        params = {
            destinationArn: destinationArn, 
            filterName: 'SumoLGLBDFilter',
            filterPattern: '',
            logGroupName: lambdaLogGroupName
        };
    } else {
        params = {
            destinationArn: destinationArn,
            filterName: 'SumoLGLBDFilter',
            filterPattern: '',
            logGroupName: lambdaLogGroupName,
            roleArn: roleArn
        };
    }

    // handle the case where the subscription filter exists / case where the log group is generated by the target lambda
    try {
        const cmd = new PutSubscriptionFilterCommand(params);
        await cwl.send(cmd);
        console.log("Successfully subscribed logGroup: ", lambdaLogGroupName);
    } catch (err) {
        console.log("Error in subscribing", lambdaLogGroupName, err);
        throw err;
    }
}

function filterLogGroups(event, logGroupRegex) {
    logGroupRegex = new RegExp(logGroupRegex, "i");
    let logGroupName = event.detail.requestParameters.logGroupName;
    if (logGroupName.match(logGroupRegex) && event.detail.eventName === "CreateLogGroup") {
        return true;
    }
    let lg_tags = event.detail.requestParameters.tags;
    if (process.env.LOG_GROUP_TAGS && lg_tags) {
        console.log("tags in loggroup: ", lg_tags);
        var tags_array = process.env.LOG_GROUP_TAGS.split(",");
        let tag, key, value;
        for (let i = 0; i < tags_array.length; i++) {
            tag = tags_array[i].split("=");
            key = tag[0].trim();
            value = tag[1].trim();
            if (lg_tags[key] && lg_tags[key] == value) {
                return true;
            }
        }
    }
    return false;
}

async function subscribeExistingLogGroups(logGroups, retryCounter) {
    var logGroupRegex = new RegExp(process.env.LOG_GROUP_PATTERN, "i");
    var destinationArn = process.env.DESTINATION_ARN;
    var roleArn = process.env.ROLE_ARN;
    const failedLogGroupNames = [];
    await logGroups.reduce(async (previousPromise, nextLogGroup) => {
        await previousPromise;
        const { logGroupName } = nextLogGroup;
        if (!logGroupName.match(logGroupRegex)) {
            console.log("Unmatched logGroup: ", logGroupName);
            return Promise.resolve();
        } else {
            return createSubscriptionFilter(logGroupName, destinationArn, roleArn).catch(function (err) {
                if (err && err.code == "ThrottlingException") {
                    failedLogGroupNames.push({ logGroupName: logGroupName });
                }
            });
        }
    }, Promise.resolve());

    if (retryCounter <= maxRetryCounter && failedLogGroupNames.length > 0) {
        console.log("Retrying Subscription for Failed Log Groups due to throttling with counter number as " + retryCounter);
        await subscribeExistingLogGroups(failedLogGroupNames, retryCounter + 1);
    }
}

async function processExistingLogGroups(token, context, errorHandler) {
    var params = { limit: 50 };
    if (token) {
      params = {
        limit: 50,
        nextToken: token
      };
    }
  
    try {
      const data = await cwl.send(new DescribeLogGroupsCommand(params));
      console.log(
        "fetched logGroups: " + data.logGroups.length + " nextToken: " + data.nextToken
      );
      await subscribeExistingLogGroups(data.logGroups, 1);
  
      if (data.nextToken) {
        console.log(
          "Log Groups remaining...Calling the lambda again with token " + data.nextToken
        );
        await invoke_lambda(context, data.nextToken, errorHandler);
        console.log("Lambda invoke complete with token " + data.nextToken);
      } else {
        console.log("All Log Groups are subscribed to Destination Type " + process.env.DESTINATION_ARN);
        errorHandler(null, "Success");
      }
    } catch (err) {
      errorHandler(err, "Error in fetching logGroups");
    }
  }
  
  async function invoke_lambda(context, token, errorHandler) {
    var payload = { "existingLogs": "true", "token": token };
    try {
      await lambda.send(new InvokeCommand({
        InvocationType: 'Event',
        FunctionName: context.functionName,
        Payload: JSON.stringify(payload)
      }));
    } catch (err) {
      errorHandler(err, "Error invoking Lambda");
    }
  }
  
  async function processEvents(env, event, errorHandler) {
    var logGroupName = event.detail.requestParameters.logGroupName;
    if (filterLogGroups(event, env.LOG_GROUP_PATTERN)) {
      console.log("Subscribing: ", logGroupName, env.DESTINATION_ARN);
      await createSubscriptionFilter(logGroupName, env.DESTINATION_ARN, env.ROLE_ARN)
        .catch(function (err) {
          errorHandler(err, "Error in Subscribing.");
        });
    } else {
      console.log("Unmatched: ", logGroupName, env.DESTINATION_ARN);
    }
  }
  
  exports.handler = async function (event, context, callback) {
    console.log("Invoking Log Group connector function");
    function errorHandler(err, msg) {
      if (err) {
        console.log(err, msg);
        callback(err);
      } else {
        callback(null, "Success");
      }
    }
    if (event.existingLogs == "true") {
      await processExistingLogGroups(event.token, context, errorHandler);
    } else {
      await processEvents(process.env, event, errorHandler);
    }
  };