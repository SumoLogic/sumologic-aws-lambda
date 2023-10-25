const { processLogs: processLogsHandler, getEndpointURL } = require('./cloudwatchlogs_lambda');
const { DLQUtils } = require("./sumo-dlq-function-utils");

const { Messages, invokeLambdas } = DLQUtils;

exports.consumeMessages = async function (env, context, callback) {
    const MessagesObj = new Messages(env);
    env.SUMO_CLIENT_HEADER = "dlq-aws-lambda";

    if (!env.SUMO_ENDPOINT) {
        try {
            let SUMO_ENDPOINT = await getEndpointURL();
            env.SUMO_ENDPOINT = SUMO_ENDPOINT;
        } catch (error) {
            console.log("Error in getEndpointURL: ", error);
            callback(error, null);
            return;
        }
    } else {
        console.log("consumeMessages: Getting SUMO_ENDPOINT from env");
    }

    try {
        const messages = await MessagesObj.receiveMessages(10);


        if (messages && messages.length > 0) {
            let fail_cnt = 0, msgCount = 0;
            console.log("Messages Received", messages.length);

            for (let i = 0; i < messages.length; i++) {
                (function (idx) {
                    const payload = JSON.parse(messages[idx].Body);
                    const receiptHandle = messages[idx].ReceiptHandle;

                    if (!(payload.awslogs && payload.awslogs.data)) {
                        console.log("Message does not contain awslogs or awslogs.data attributes", payload);

                        MessagesObj.deleteMessage(receiptHandle)
                            .catch((err) => console.log(err, err.stack));

                        return;
                    }

                    const logdata = payload.awslogs.data;

                    processLogsHandler(env, logdata, function (err, msg) {
                        msgCount++;

                        if (err) {
                            console.log(err, msg);
                            fail_cnt++;
                        } else {
                            MessagesObj.deleteMessage(receiptHandle)
                                .catch((err) => console.log(err, err.stack));
                        }

                        if (msgCount === messages.length) {
                            if (fail_cnt === 0 && parseInt(env.is_worker) === 0) {
                                invokeLambdas(env.AWS_REGION, parseInt(env.NUM_OF_WORKERS),
                                    context.functionName, '{"is_worker": "1"}', context);
                            }

                            callback(null, `${messages.length - fail_cnt} success`);
                        }
                    });
                })(i);
            }
        } else {

            callback(null, 'success');
        }
    } catch (error) {
        callback(error);
    }
};

exports.handler = function (event, context, callback) {
    const env = Object.assign({}, process.env);
    env.is_worker = event.is_worker || 0;
    exports.consumeMessages(env, context, callback);
};