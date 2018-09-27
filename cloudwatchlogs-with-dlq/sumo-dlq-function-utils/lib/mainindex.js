var SumoLogsClient = require('./sumologsclient.js').SumoLogsClient;
var generateHeaders = require('./sumologsclient.js').generateHeaders;
var Messages = require('./dlqutils.js').Messages;
var AWSUtils = require('./awsutils.js');

module.exports = {
    SumoLogsClient: SumoLogsClient,
    Messages: Messages,
    AWSUtils: AWSUtils,
    generateHeaders: generateHeaders
};
