///////////////////////////////////////////////////////////////////////////////////////////////////////////
// Remember to change the hostname and path to match your collection API and specific HTTP-source endpoint
// See more at: https://service.sumologic.com/help/Default.htm#Collector_Management_API.htm
///////////////////////////////////////////////////////////////////////////////////////////////////////////
var sumoEndpoint = 'https://collectors.sumologic.com/receiver/v1/http/<XXX>'

var https = require('https');
var zlib = require('zlib');
var url = require('url');

exports.handler = function(event, context) {
	    var urlObject = url.parse(sumoEndpoint);
	    
	    var options = { 'hostname': urlobject.hostname,
				'path': urlObject.pathname,
				'method': 'POST'
			};
		var zippedInput = new Buffer(event.awslogs.data, 'base64');

		zlib.gunzip(zippedInput, function(e, buffer) {
			if (e) { context.fail(e); }       

			awslogsData = JSON.parse(buffer.toString('ascii'));

			console.log(awslogsData);

			if (awslogsData.messageType === "CONTROL_MESSAGE") {
				console.log("Control message");
				context.succeed("Success");
			}

			var req = https.request(options, function(res) {
				var body = '';
				console.log('Status:', res.statusCode);
				res.setEncoding('utf8');
				res.on('data', function(chunk) { body += chunk; });
				res.on('end', function() {
					console.log('Successfully processed HTTPS response');
					context.succeed(); });
			});

			req.on('error', context.fail);

			stream=awslogsData.logStream;
			group=awslogsData.logGroup;

			curRequestID = null;
			var re = new RegExp(/RequestId: (\S+) /);
			awslogsData.logEvents.forEach(function(val, idx, arr) {
				val.logStream = stream;
				val.logGroup = group;
				var rs = re.exec(val.message);
				if (rs!=null) { curRequestID = rs[1]; }
				val.requestID = curRequestID;
				req.write(JSON.stringify(val) + '\n');
			});
			req.end();
		});    
};

