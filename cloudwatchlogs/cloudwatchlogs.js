
var https = require('https');
var zlib = require('zlib');

exports.handler = function(event, context) {
		///////////////////////////////////////////////////////////////////////////////////////////////////////////
		// Remember to change the hostname and path to match your collection API and specific HTTP-source endpoint
		// See more at: https://service.sumologic.com/help/Default.htm#Collector_Management_API.htm
		///////////////////////////////////////////////////////////////////////////////////////////////////////////
	    var options = { 'hostname': 'collectors.sumologic.com',
						'path': 'receiver/v1/http/<XXX>',
						'method': 'POST'
					};
		var zippedInput = new Buffer(event.awslogs.data, 'base64');

		zlib.gunzip(zippedInput, function(e, buffer) {
			if (e) { context.fail(e); }       

			awslogsData = JSON.parse(buffer.toString('ascii'));

			//console.log(awslogsData);

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
					context.succeed("Success"); });
			});

			req.on('error', context.fail);

			stream=awslogsData.logStream;
			group=awslogsData.logGroup;
			awslogsData.logEvents.forEach(function(val, idx, arr) {
				val.logStream = stream;
				val.logGroup = group;
				req.write(JSON.stringify(val) + '\n');
				});
			req.end();
		});    
};

