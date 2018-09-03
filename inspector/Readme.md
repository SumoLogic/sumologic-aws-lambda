# SumoLogic Lambda Function for Amazon Inspector

This function receives the records published to a SNS Topic by Amazon Inspector.It looks up an Inspector object based on its arn and type and then adds extra context to the final messages which are compressed and send to Sumo Logic HTTP source endpoint.

## Lambda Setup((docs)[https://help.sumologic.com/Send-Data/Applications-and-Other-Data-Sources/Amazon-Inspector-App/01-Collect-Data-for-Amazon-Inspector])

### Create an Amazon SNS Topic
1. Login to the Amazon Console.
2. Go to Application Integration > Simple Notification Service (SNS).
3. On the SNS Dashboard, select Create topic.
4. Enter a Topic name and a Display name, and click Create topic.
5. To assign the following policy to this topic, select the topic, then under Advanced view, click Actions/Edit topic policy.
6. Replace the existing text with the following:
```
{
 "Version": "2008-10-17",
 "Id": "inspector-sns-publish-policy",
 "Statement": [
   {
     "Sid": "inspector-sns-publish-statement",
     "Effect": "Allow",
     "Principal": {
       "Service": "inspector.amazonaws.com"
     },
     "Action": "SNS:Publish",
     "Resource": "arn:aws:sns:*"
   }
 ]
}
```
7. Click Update policy.

### Configure Amazon Inspector
1. In the Amazon Console, go to Security, Identity & Compliance > Inspector.
2. Select each assessment template you want to monitor.
3. Expand each row and find the section called SNS topics.
4. Click the Edit icon and select the SNS topic you created in the previous section.
5. Click Save.

### Create a Role
In the Amazon Console, go to Security, Identity & Compliance > IAM.
Create a new role called Lambda-Inspector.

### Create a Lambda Function
1. In the Amazon Console, go to Compute > Lambda.
2. Create a new function.
3. On the Select blueprint page, select a Blank function.
4. Select the SNS topic you created in Create an Amazon SNS Topic as trigger.
5. Click Next.
6. On the Configure function page, enter a name for the function.
7. Go to https://github.com/SumoLogic/sumologic-aws-lambda/blob/master/inspector/python/inspector.py and copy and paste the sumologic-aws-lambda code into the field.
8. Edit the code to enter the URL of the Sumo Logic endpoint that will receive data from the HTTP Source.
9. Scroll down and configure the rest of the settings as follows:
   Memory (MB). 128.
   Timeout. 5 min.
   VPC. No VCP.
10. Click Next.
11. Click Create function.
