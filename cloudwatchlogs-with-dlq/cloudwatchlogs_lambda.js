/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//                                        CloudWatch Logs to SumoLogic                                             //
//               https://github.com/SumoLogic/sumologic-aws-lambda/tree/master/cloudwatchlogs                      //
//                                                                                                                 //
//        YOU MUST CREATE A SUMO LOGIC ENDPOINT CALLED SUMO_ENDPOINT AND PASTE IN ENVIRONMENTAL VARIABLES BELOW    //
//            https://help.sumologic.com/Send_Data/Sources/02Sources_for_Hosted_Collectors/HTTP_Source             //
/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Include logStream and logGroup as json fields within the message. Required for SumoLogic AWS Lambda App

// Regex used to detect logs coming from lambda functions.
// The regex will parse out the requestID and strip the timestamp
// Example: 2016-11-10T23:11:54.523Z    108af3bb-a79b-11e6-8bd7-91c363cc05d9    some message
var consoleFormatRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z\s(\w+?-\w+?-\w+?-\w+?-\w+)\s(INFO|ERROR|WARN|DEBUG)?/;

// Used to extract RequestID
var requestIdRegex = /(?:RequestId:|Z)\s+([\w\d\-]+)/;
var url = require('url');
var vpcutils = require('./vpcutils');
var SumoLogsClient = require('./sumo-dlq-function-utils').SumoLogsClient;
var Utils = require('./sumo-dlq-function-utils').Utils;
const AWS = require('aws-sdk');
const ssm = new AWS.SSM();

exports.getEndpointURL = async function() {
  console.log('Getting SUMO_ENDPOINT from AWS SSM Parameter Store');
  return new Promise((resolve, reject) => {
    ssm.getParameter(
      {
        Name: 'SUMO_ENDPOINT',
        WithDecryption: true
      },
      (err, data) => {
        if (err) {
          console.log(err, err.stack);
          reject(new Error('Unable to get EndpointURL from SSM: ' + err));
        } else {
          // console.log(data);
          resolve(data.Parameter.Value);
        }
      }
    );
  });
}

function createRecords(config, events, awslogsData) {
    var records = [];
    var lastRequestID = null;
    console.log('Log events: ' + events.length);

    events.forEach(function (log) {
        // Remove any trailing \n
        log.message = log.message.replace(/\n$/, '');
        // Try extract requestID
        var requestId = requestIdRegex.exec(log.message);
        if (requestId !== null) {
            lastRequestID = requestId[1];
        }
        // Attempt to detect console log and auto extract requestID and message
        var consoleLog = consoleFormatRegex.exec(log.message);
        if (consoleLog !== null) {
            lastRequestID = consoleLog[1];
            log.message = log.message.substring(consoleLog[0].length);
        }
        if (lastRequestID) {
            log.requestID = lastRequestID;
        }
        // Auto detect if message is json
        try {
            log.message = JSON.parse(log.message);
        } catch (err) {
            // Do nothing, leave as text
            log.message = log.message.trim();
        }
        // delete id as it's not very useful
        delete log.id;
        if (config.LogFormat.startsWith("VPC")) {
            delete log.timestamp;
        }
        delete log.extractedFields;

        if (config.includeLogInfo) {
            log.logStream = awslogsData.logStream;
            log.logGroup = awslogsData.logGroup;
        }
        records.push(log);
    });
    return records;
}

async function getConfig(env) {

    var config = {
        // The following parameters override the sourceCategory, sourceHost, sourceName and sourceFields metadata fields within SumoLogic.
        // Not these can also be overridden via json within the message payload. See the README for more information.
        "sourceCategoryOverride": ("SOURCE_CATEGORY_OVERRIDE" in env) ?  env.SOURCE_CATEGORY_OVERRIDE: '',  // If none sourceCategoryOverride will not be overridden
        "sourceFieldsOverride": ("SOURCE_FIELDS_OVERRIDE" in env) ?  env.SOURCE_FIELDS_OVERRIDE: '',        // If none sourceFieldsOverride will not be overridden
        "sourceHostOverride": ("SOURCE_HOST_OVERRIDE" in env) ? env.SOURCE_HOST_OVERRIDE : '',              // If none sourceHostOverride will not be set to the name of the logGroup
        "sourceNameOverride": ("SOURCE_NAME_OVERRIDE" in env) ? env.SOURCE_NAME_OVERRIDE : '',              // If none sourceNameOverride will not be set to the name of the logStream
        "SUMO_CLIENT_HEADER": env.SUMO_CLIENT_HEADER || 'cwl-aws-lambda',
        // CloudWatch logs encoding
        "encoding": env.ENCODING || 'utf-8',  // default is utf-8
        "LogFormat": env.LOG_FORMAT || 'Others',
        "compressData": env.COMPRESS_DATA || true,
        "vpcCIDRPrefix": env.VPC_CIDR_PREFIX || '',
        "includeLogInfo": ("INCLUDE_LOG_INFO" in env) ? env.INCLUDE_LOG_INFO === "true" : false,
        "includeSecurityGroupInfo": ("INCLUDE_SECURITY_GROUP_INFO" in env) ? env.INCLUDE_SECURITY_GROUP_INFO === "true" : false,
        // Regex to filter by logStream name prefixes
        "logStreamPrefixRegex": ("LOG_STREAM_PREFIX" in env)
                                ? new RegExp('^(' + escapeRegExp(env.LOG_STREAM_PREFIX).replace(/,/g, '|')  + ')', 'i')
                                : ''
    };
    if (!env.SUMO_ENDPOINT) {
        config['SumoURL'] = await exports.getEndpointURL();
        if (config['SumoURL'] instanceof Error) {
            return new Error('Either define SUMO_ENDPOINT environment variable or create a secure string named /sumologic/SUMO_ENDPOINT in SSM');
        }
    } else {
        console.log("getConfig: getting SUMO_ENDPOINT from env");
        config['SumoURL'] = env.SUMO_ENDPOINT;
    }

    // Validate URL has been set
    var urlObject = url.parse(config.SumoURL);
    if (urlObject.protocol !== 'https:' || urlObject.host === null || urlObject.path === null) {
        return new Error('Invalid SUMO_ENDPOINT environment variable: ' + config.SumoURL);
    }
    return config;
}

function escapeRegExp(string) {
  return string.replace(/[|\\{}()[\]^$+*?.-]/g, '\\$&');
}

function transformRecords(config, records) {
    return new Promise(function (resolve, reject) {
        if (config.LogFormat === "VPC-JSON" && config.includeSecurityGroupInfo) {
            vpcutils.includeSecurityGroupIds(records).then(function (modifiedRecords) {
                if (modifiedRecords && modifiedRecords.length > 0 && "security-group-ids" in modifiedRecords[0]) {
                    console.log("SecurityGroupInfo Added");
                }
                resolve(modifiedRecords);
            });
        } else {
            resolve(records);
        }
    });
}

function filterRecords(config, records) {
    var filteredRecords = records;
    if (config.LogFormat.startsWith("VPC") && config.vpcCIDRPrefix) {
        filteredRecords = vpcutils.discardInternalTraffic(config.vpcCIDRPrefix, records);
        console.log(records.length - filteredRecords.length + " records discarded as InternalTraffic");
    }
    return filteredRecords;
}

exports.processLogs = async function (env, eventAwslogsData, callback) {
    var zippedInput = Buffer.from(eventAwslogsData, 'base64');
    var config = await getConfig(env);
    if (config instanceof Error) {
        console.log("Error in getConfig: ", config);
        callback(config, null);
        return;
    }
    var awslogsData;
    Utils.gunzipPromise(zippedInput).then(function (data) {
        console.log("Successfully Unzipped");
        awslogsData = JSON.parse(data.toString(config.encoding));
        var records = [];
        if (awslogsData.messageType === 'CONTROL_MESSAGE') {
            console.log('Skipping Control Message');
        } else if(config.logStreamPrefixRegex && !awslogsData.logStream.match(config.logStreamPrefixRegex)){
            console.log('Skipping Non-Applicable Log Stream');
        } else {
            records = createRecords(config, awslogsData.logEvents, awslogsData);
            console.log(records.length + " Records Found");
        }
        return records;
    }).then(function (records) {
        records = filterRecords(config, records);
        if (records.length > 0) {
            return transformRecords(config, records).then(function (records) {
                var SumoLogsClientObj = new SumoLogsClient(config);
                var messageList = SumoLogsClientObj.createBuckets(config, records, awslogsData, config.LogFormat === "VPC-RAW");
                console.log("Buckets Created: " + Object.keys(messageList).length);
                // console.log(messageList);
                return SumoLogsClientObj.postToSumo(messageList, config.compressData);
            });
        }
    }).then(function (result) {
        if (!result) {
            callback(null, "No Records");
        } else {
            var msg = `RequestSent: ${result.requestSuccessCnt} RequestError: ${result.messageErrors.length}`;
            console.log(msg);
            callback(result.messageErrors.length > 0 ? result.messageErrors.join() : null, msg);
        }
    }).catch(function (err) {
        console.log(err);
        callback(err, null);
    });
};

exports.handler = function (event, context, callback) {

    exports.processLogs(process.env, event.awslogs.data, callback);

};
