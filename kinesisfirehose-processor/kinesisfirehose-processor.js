function encodebase64(data) {
    return (Buffer.from(data, 'utf8')).toString('base64');
}

function decodebase64(data) {
    return (Buffer.from(data, 'base64')).toString('utf8');
}

function addDelimitertoJSON(data, delimiter) {
    delimiter = typeof delimiter === 'undefined' ? '\n' : delimiter;
    let resultdata = decodebase64(data);
    resultdata = resultdata + delimiter;
    resultdata = encodebase64(resultdata);
    return resultdata;
}

function convertToLine(data) {
    // converts json object to a single line ({k1:v1,k2:v2} to k1=v1 k2=v2)
    const entryObj = JSON.parse(decodebase64(data));
    var resultdata = "";
    for (var key in entryObj) {
        if (entryObj.hasOwnProperty(key)) {
            resultdata += key + "=" + entryObj[key] + " ";
        }
    }
    resultdata = resultdata.trim() + "\n";
    resultdata = encodebase64(resultdata);
    return resultdata;
}
exports.handler = (event, context, callback) => {
    console.log("invoking transformation lambda");
    let success = 0;
    let failure = 0;

    const output = event.records.map( function (record) {
        try {
            // let resultdata = convertToLine(record.data);
            let resultdata = addDelimitertoJSON(record.data);
            success++;
            return {
                recordId: record.recordId,
                result: 'Ok',
                data: resultdata
            };
        } catch(error) {
            console.log("Error in record transformation", error);
            failure++;
            return {
                recordId: record.recordId,
                result: 'ProcessingFailed',
                data: record.data,
            };
        }
    });
    console.log(`Processing completed.Total records ${output.length}. Success ${success} Failed ${failure}`);
    callback(null, { records: output });
};
