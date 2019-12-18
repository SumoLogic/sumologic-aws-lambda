var https = require('https');
var zlib = require('zlib');
var stream = require('stream');

var encodebase64 = function (data) {
    return (Buffer.from(data, 'utf8')).toString('base64');
};

var decodebase64 = function (data) {
    return (Buffer.from(data, 'base64')).toString('utf8');
};

Promise.retryMax = function (fn, retry, interval, fnParams) {
    return fn.apply(this, fnParams).catch((err) => {
        var waitTime = typeof interval === 'function' ? interval() : interval;
        console.log("Retries left " + (retry-1) + " delay(in ms) " + waitTime);
        return (retry > 1? Promise.wait(waitTime).then(() => Promise.retryMax(fn, retry-1, interval, fnParams)): Promise.reject(err));
    });
};

Promise.wait = function (delay) {
    return new Promise((fulfill, reject)=> {
        //console.log(Date.now());
        setTimeout(fulfill, delay || 0);
    });
};

var exponentialBackoff = function (seed) {
    var count = 0;
    return function () {
        count += 1;
        return count * seed;
    };
};

var filterObj = function (obj, predicate) {
    var result = {}, key;
    for (key in obj) {
        if (obj.hasOwnProperty(key) && !predicate(obj[key])) {
            result[key] = obj[key];
        }
    }
    return result;
}
var gunzipPromise = function (buffer) {
    // to make it backward compatible for multiple concatenated members https://github.com/nodejs/node/pull/5120
    return new Promise(function (resolve, reject) {
        var uncompressed_bytes = [];
        var gunzip = zlib.createGunzip();
        gunzip.on('data', function (data) {
            uncompressed_bytes.push(data.toString());
        }).on("end", function () {
            resolve(uncompressed_bytes.join(""));
        }).on("error", function (e) {
            reject(e);
        });
        var bufferStream = new stream.PassThrough();
        bufferStream.end(buffer);
        bufferStream.pipe(gunzip);
    });
};
/*Server Errors Ex 429 throttling are thrown inside onEnd
Following Errors are thrown inside onError
ECONNRESET - server closed the socket unexpectedly
ECONNREFUSED - server did not listen
HPE_* codes - server returned garbage
*/
var sendRequest = function (Options, data) {
    return new Promise(function (resolve, reject) {
        var req = https.request(Options, function (res) {
            var body = '';
            res.setEncoding('utf8');
            res.on('data', function (chunk) {
                body += chunk;
            });
            res.on('end', function () {
                if (res.statusCode === 200) {
                    resolve({"status": "SUCCESS", "response": res});
                } else {
                    reject({"status": "FAILED", "response": res});
                }
            });
        });
        req.on('error', function (err) {
            reject({"status": "FAILED", "error": err});
        });
        req.write(data);
        req.end();
    });
};

var compressData = function(Options, data) {
    return new Promise(function (resolve, reject) {
        Options.headers['Content-Encoding'] = 'gzip';
        zlib.gzip(data,function(err,compressed_data){
            if (!err)  {
                console.log("Data Compressed");
               resolve(compressed_data);
            } else {
                console.log("Failed to CompressData", err);
                reject(err);
            }
        });
    });
}

module.exports = {
    encodebase64: encodebase64,
    decodebase64: decodebase64,
    p_retryMax: Promise.retryMax,
    p_wait: Promise.wait,
    exponentialBackoff: exponentialBackoff,
    gunzipPromise: gunzipPromise,
    sendRequest: sendRequest,
    filterObj: filterObj,
    compressData: compressData
};

