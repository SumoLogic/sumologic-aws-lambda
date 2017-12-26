var https = require('https');
var url = require('url');

function SumoLogsClient(config) {
    this.options = config.options || {};
    if (config.SumoURL) {
        var urlObj = url.parse(config.SumoURL);
        this.options.hostname = urlObj.hostname;
        this.options.path = urlObj.pathname;
        this.options.protocol = urlObj.protocol;
    }
    this.options.method = 'POST';
}

function generateHeaders(config, message, awslogsData) {
    var sourceCategory = config.sourceCategoryOverride || '';
    var sourceName = config.sourceNameOverride || ((awslogsData) ? awslogsData.logStream : '');
    var sourceHost = config.sourceHostOverride || ((awslogsData) ? awslogsData.logGroup : '');

    var headerObj = {
        'X-Sumo-Name':sourceName, 'X-Sumo-Category':sourceCategory,
        'X-Sumo-Host':sourceHost, 'X-Sumo-Client': config.SUMO_CLIENT_HEADER
    };

    var metadataMap = { 'source': 'X-Sumo-Name', 'category': 'X-Sumo-Category', 'host': 'X-Sumo-Host'};
    if (message.hasOwnProperty('_sumo_metadata')) {
        var metadataOverride = message._sumo_metadata;
        Object.getOwnPropertyNames(metadataOverride).forEach( function(property) {
            if (metadataMap[property]) { //format for metadatamap keys soureName(in azure) or name
                var targetProperty = metadataMap[property];
                headerObj[targetProperty] = metadataOverride[property];
            }
        });
        delete message._sumo_metadata;
    }
    return headerObj;
}

SumoLogsClient.prototype.postToSumo = function (messages, errorHandler, beforeRequest) {
    var messagesTotal = Object.keys(messages).length;
    var messagesSent = 0;
    var messageErrors = [];

    var finalizeContext = function () {
        var total = messagesSent + messageErrors.length;
        if (total == messagesTotal) {
            console.log('messagesSent: ' + messagesSent + ' messagesErrors: ' + messageErrors.length);
            errorHandler(null, 'messagesSent: ' + messagesSent + ' messagesErrors: ' + messageErrors.length); // what if some fail and some got success status should be what
        }
    };
    var thatOptions = this.options;
    Object.keys(messages).forEach(function (key, index) {
        if (beforeRequest) {
            beforeRequest(thatOptions, messages, key);
        }

        var req = https.request(thatOptions, function (res) {
            res.setEncoding('utf8');
            res.on('data', function (chunk) {}); // why this is empty
            res.on('end', function () {
                if (res.statusCode == 200) {
                    messagesSent++;
                } else {
                    messageErrors.push('HTTP Return code ' + res.statusCode);
                }
                finalizeContext();
            });
        });

        req.on('error', function (e) {
            messageErrors.push(e.message);
            finalizeContext();
        });

        for (var i = 0; i < messages[key].length; i++) {
            req.write(JSON.stringify(messages[key][i]) + '\n');
        }
        req.end();
    });
}
module.exports = {
    SumoLogsClient: SumoLogsClient,
    generateHeaders: generateHeaders
};
