function sampleTraffic(samplingPercent, records) {
    if (!samplingPercent) {
        return records;
    }
    var filteredRecords = [];
    var toBeSamplesRecords = [];
    records.forEach(function (log) {
        if ("logLevel" in log.message.message) {
            if(Number.isInteger(log.message.message.logLevel)){
                if (log.message.message.logLevel >= 4) {
                    filteredRecords.push(log);
                } else {
                    toBeSamplesRecords.push(log);
                }
            } else {
                filteredRecords.push(log);
            }
        } else {
            filteredRecords.push(log);
        }
    });
    if(samplingPercent == 0) {
        var increment = 0;
    } else {
        var increment = 100/samplingPercent;
    }
    
    if(increment > 0) {
        for (var i = 0; i < toBeSamplesRecords.length; i += increment) {
            filteredRecords.push(toBeSamplesRecords[i]);
        }
    }
    return filteredRecords;
}

module.exports = {
    sampleTraffic: sampleTraffic
};