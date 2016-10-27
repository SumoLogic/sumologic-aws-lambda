var https = require('https');

///////////////////////////////////////////////////////////////////////////////////////////////////////////
// Remember to change the hostname and path to match your collection API and specific HTTP-source endpoint
// See more at: https://service.sumologic.com/help/Default.htm#Collector_Management_API.htm
///////////////////////////////////////////////////////////////////////////////////////////////////////////
var options = { 'hostname': 'endpoint1.collection.us2.sumologic.com',
  'path': 'https://endpoint1.collection.us2.sumologic.com/receiver/v1/http/XXXXX',
  'method': 'POST'
};

exports.handler = function(event, context) {

  var req = https.request(options, function(res) {
      var body = '';
      console.log('Status:', res.statusCode);
      res.setEncoding('utf8');
      res.on('data', function(chunk) { body += chunk; });
      res.on('end', function() {
        console.log('Successfully processed HTTPS response');
        context.succeed(); });
    });

  options.agent = new https.Agent(options);

  req.on('error', context.fail);

  event.Records.forEach(function(record) {
    var payload = new Buffer(record.kinesis.data, 'base64').toString('ascii');
    req.write(payload + '\n');
  })
  req.end();

}
