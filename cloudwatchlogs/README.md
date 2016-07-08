Sumo Logic Functions for AWS CloudWatch Logs 
===========================================

Files 
-----
*	*cloudwatchlogs.js*:  node.js file to collect data from AWS CWL. Can also be used to collect AWS VPC Flowlogs sent via CWL.
*	*cloudwatchlogs_lambda.js*:  node.js file to collect AWS Lambda logs via CWL. This version extracts and add a "RequestId" field to each log line to make correlations easier.

Usage
-----
1. First create an HTTP source endpoint on the Sumo side. You will need this endpoint for the lambda function later.
2. Goto AWS CloudWatch Logs console, check the Log Group you want to send data to Sumologic. From Actions button, select "Start Streaming to Lambda Service", then "Create a Lambda function"
3. Skip the blueprint
4. Copy the relevant lambda function to the console. **REMEMBER** to replace the value of *hostname* in the function with the relevant value for your SumoLogic account, and of the *path* with HTTP endpoint created in the first step above. 
5. Scroll down to the *Lambda function handle and role* section, make sure you set the right values that match the function. For role, you can just use the basic execution role. Click next.
6. Finally click on "Create function" to create the function. 
7. (Optional) Test this new function with sample AWS CloudWatch Logs template provided by AWS  
NOTE: If you are interested in **Lambda logs** (via CloudWatchLogs) specifically, please visit this [KB article](http://help.sumologic.com/Apps/AWS_Lambda/Collect_Logs_for_AWS_Lambda?t=1461360129021)  


