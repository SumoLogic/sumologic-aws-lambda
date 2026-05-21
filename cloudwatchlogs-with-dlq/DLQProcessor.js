const { processLogs: processLogsHandler, getEndpointURL } = require('./cloudwatchlogs_lambda');
const { DLQUtils } = require("./sumo-dlq-function-utils");

const { Messages, invokeLambdas } = DLQUtils;

exports.consumeMessages = async function (env, context) {
    const MessagesObj = new Messages(env);
    env.SUMO_CLIENT_HEADER = "dlq-aws-lambda";

    if (!env.SUMO_ENDPOINT) {
        let SUMO_ENDPOINT = await getEndpointURL();
        env.SUMO_ENDPOINT = SUMO_ENDPOINT;
    } else {
        console.log("consumeMessages: Getting SUMO_ENDPOINT from env");
    }

    const messages = await MessagesObj.receiveMessages(10);

    if (messages && messages.length > 0) {
        let fail_cnt = 0;
        console.log("Messages Received", messages.length);

        for (let i = 0; i < messages.length; i++) {
            const payload = JSON.parse(messages[i].Body);
            const receiptHandle = messages[i].ReceiptHandle;

            if (!(payload.awslogs && payload.awslogs.data)) {
                console.log("Message does not contain awslogs or awslogs.data attributes", payload);
                MessagesObj.deleteMessage(receiptHandle)
                    .catch((err) => console.log(err, err.stack));
                continue;
            }

            const logdata = payload.awslogs.data;

            try {
                await processLogsHandler(env, logdata);
                MessagesObj.deleteMessage(receiptHandle)
                    .catch((err) => console.log(err, err.stack));
            } catch (err) {
                console.log(err);
                fail_cnt++;
            }
        }

        if (fail_cnt === 0 && parseInt(env.is_worker) === 0) {
            invokeLambdas(env.AWS_REGION, parseInt(env.NUM_OF_WORKERS),
                context.functionName, '{"is_worker": "1"}', context);
        }

        return `${messages.length - fail_cnt} success`;
    } else {
        return 'success';
    }
};

exports.handler = async function (event, context) {
    const env = Object.assign({}, process.env);
    env.is_worker = event.is_worker || 0;
    return await exports.consumeMessages(env, context);
};