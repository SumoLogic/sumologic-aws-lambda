var url = require('url');
var utils = require('./utils');

function SumoLogsClient(config) {
    this.options = config.options || {};
    if (config.SumoURL) {
        var urlObj = url.parse(config.SumoURL);
        this.options.hostname = urlObj.hostname;
        this.options.path = urlObj.pathname;
        this.options.protocol = urlObj.protocol;
    }
    this.options.method = 'POST';
    this.SUMO_CLIENT_HEADER = config.SUMO_CLIENT_HEADER;
}

SumoLogsClient.prototype.generateHeaders = function(config, message, awslogsData) {
    var sourceCategory = config.sourceCategoryOverride || '';
    var sourceFields = config.sourceFieldsOverride || '';
    var sourceName = config.sourceNameOverride || ((awslogsData) ? awslogsData.logStream : '');
    var sourceHost = config.sourceHostOverride || ((awslogsData) ? awslogsData.logGroup : '');

    var headerObj = {
        'X-Sumo-Name':sourceName, 'X-Sumo-Category':sourceCategory,
        'X-Sumo-Host':sourceHost, 'X-Sumo-Fields':sourceFields,
        'X-Sumo-Client': config.SUMO_CLIENT_HEADER
    };

    var metadataMap = {category: "X-Sumo-Category", sourceName: "X-Sumo-Name", sourceHost: "X-Sumo-Host", sourceFieldsOverride: "X-Sumo-Fields"};
    if (message.hasOwnProperty('_sumo_metadata')) {
        var metadataOverride = message._sumo_metadata;
        Object.getOwnPropertyNames(metadataOverride).forEach( function(property) {
            if (metadataMap[property]) {
                var targetProperty = metadataMap[property];
            } else {
                targetProperty = property;
            }
            headerObj[targetProperty] = metadataOverride[property];
        });
        delete message._sumo_metadata;
    }
    return headerObj;
};

SumoLogsClient.prototype.createPromises = function(messages, is_compressed) {
    var self = this;
    return Object.keys(messages).map(function (key) {
        var headerArray = key.split(':');
        var headers = {
            'X-Sumo-Name': headerArray[0],
            'X-Sumo-Category': headerArray[1],
            'X-Sumo-Host': headerArray[2],
            'X-Sumo-Fields': headerArray[3],
            'X-Sumo-Client': self.SUMO_CLIENT_HEADER
        };
        var options = Object.assign({}, self.options);
        // removing headers with 'none'
        options.headers = utils.filterObj(headers, function(k,v) {
            return v && (v.toLowerCase() !== 'none');
        });
        var data = [];
        for (var i = 0; i < messages[key].length; i++) {
            if (messages[key][i] instanceof Object) {
                data.push(JSON.stringify(messages[key][i]));
            } else {
                data.push(messages[key][i]);
            }
        }
        data = data.join("\n");
        var pdata = is_compressed ? utils.compressData(options, data) : Promise.resolve(data);

        // handling catch so that if one promise fails others would still be executed
        return pdata.then(function(payload) {
            return utils.sendRequest(options, payload);
        }).catch(function(err) {
            err.failedBucketKey = key;
            return err;
        });
    });
}

SumoLogsClient.prototype.postToSumo = function(messages, is_compressed) {
    var all_promises = this.createPromises(messages, is_compressed);
    return Promise.all(all_promises).then(function (values) {
        console.log(`${values.length} requests finished`);
        var requestSuccessCnt = 0;
        var messageErrors = [];
        var failedBucketKeys = [];
        values.forEach(function (obj) {
            if (obj.status === "SUCCESS") {
                requestSuccessCnt += 1;
            } else {
                var message = obj.error?obj.error.message:obj.response.statusMessage;
                messageErrors.push(message);
                failedBucketKeys.push(obj.failedBucketKey);
            }
        });
        return {
            requestSuccessCnt: requestSuccessCnt,
            messageErrors: messageErrors,
            failedBucketKeys: failedBucketKeys
        };
    });
};

SumoLogsClient.prototype.getMetaDataKey = function(headerObj) {
    return headerObj['X-Sumo-Name'] + ':' + headerObj['X-Sumo-Category'] + ':' + headerObj['X-Sumo-Host'] + ':' + headerObj['X-Sumo-Fields'];
};


SumoLogsClient.prototype.createBuckets = function(config, records, awslogsData, isRaw) {
    var self = this;
    var messageList = {};
    // Chunk records before posting to SumoLogic
    records.forEach(function (log, idx, arr) {
        var headerObj = self.generateHeaders(config, log.message, awslogsData);
        var metadataKey = self.getMetaDataKey(headerObj);
        var message = isRaw ? log.message : log;
        if (metadataKey in messageList) {
            messageList[metadataKey].push(message);
        } else {
            messageList[metadataKey] = [message];
        }
    });
    return messageList;
};

module.exports = {
    SumoLogsClient: SumoLogsClient
};
