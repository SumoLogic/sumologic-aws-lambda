var https = require('https');
var zlib = require('zlib');

exports.handler = function(event, context) {
		///////////////////////////////////////////////////////////////////////////////////////////////////////////
		// Remember to change the hostname and path to match your collection API and specific HTTP-source endpoint
		// See more at: https://service.sumologic.com/help/Default.htm#Collector_Management_API.htm
		///////////////////////////////////////////////////////////////////////////////////////////////////////////
		var options = {
			'hostname': 'collectors.sumologic.com',
			'path': 'receiver/v1/http/<XXX>',
			'method': 'POST'
		};
		var zippedInput = new Buffer(event.awslogs.data, 'base64');

		zlib.gunzip(zippedInput, function(e, buffer) {
			if (e) { context.fail(e); }

			var awslogsData = JSON.parse(buffer.toString('ascii'));

			console.log(awslogsData);

			if (awslogsData.messageType === "CONTROL_MESSAGE") {
				console.log("Control message");
				context.succeed("Success");
			}

			var requestsSent = 0;
			var requestsFailed = 0;
			var finalizeContext = function() {
				var tot = requestsSent + requestsFailed;
				if (tot == awslogsData.logEvents.length) {
					if (requestsFailed > 0) {
						context.fail(requestsFailed + " / " + tot + " events failed");
					} else {
						context.succeed(requestsSent + " requests sent");
					}
				}
			};

			var re = new RegExp(/(?:RequestId:|Z)\s+([\w\d\-]+)/);
			var lastRequestID = null;
			awslogsData.logEvents.forEach(function(val, idx, arr) {
				var req = https.request(options, function(res) {
					var body = '';
					console.log('Status:', res.statusCode);
					res.setEncoding('utf8');
					res.on('data', function(chunk) { body += chunk; });
					res.on('end', function() {
						console.log('Successfully processed HTTPS response');
						requestsSent++;
						finalizeContext();
					});
				});

				req.on('error', function(e) {
					console.log(e.message)
					requestsFailed++;
					finalizeContext();
				});

				var stream=awslogsData.logStream;
				var group=awslogsData.logGroup;
				var rs = re.exec(val.message);
				if (rs!==null) { 
                		   lastRequestID = rs[1]; 
                		}
				val.requestID = lastRequestID;
				val.logStream = stream;
				val.logGroup = group;
				req.end(JSON.stringify(val));
			});

		});
};
