
import json
import httplib
import base64,zlib
import urlparse
import boto3
import datetime
import logging

##################################################################
# Configuration                                                  #
##################################################################
# Enter Sumo Http source endpoint here.
sumoEndpoint = "https://endpoint1.collection.sumologic.com/receiver/v1/http/<XXXX>"
# include auxiliary data (e.g for assessment template, run, or target) in the collected event or not
contextLookup = True


##################################################################
# Main Code                                                      #
##################################################################
up = urlparse.urlparse(sumoEndpoint)
options = { 'hostname': up.hostname,
                'path': up.path,
                'method': 'POST'
            };

# Internal variables used for this Lambda function
resourceMap = {'finding':{},'target':{},'run':{},'template':{}, 'rulesPackage':{}}
# prepare logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# main function to send data to a Sumo HTTP source
def sendSumo(msg, toCompress = False):
    conn = httplib.HTTPSConnection(options['hostname'])
    if (toCompress):
        headers = {"Content-Encoding": "gzip"}
        finalData = compress(msg)
    else:
        headers = {"Content-type": "text/html","Accept": "text/plain"}
        finalData =msg
    headers.update({"X-Sumo-Client": "inspector-aws-lambda"})
    conn.request(options['method'], options['path'], finalData,headers)
    response = conn.getresponse()
    conn.close()
    return (response.status,response.reason)


# Simple function to compress data
def compress(data, compresslevel=9):
    compress = zlib.compressobj(compresslevel, zlib.DEFLATED, 16 + zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
    compressedData = compress.compress(data)
    compressedData += compress.flush()
    return compressedData

# This function looks up an Inspector object based on its arn and type. Returned object will be used to provide extra context for the final message to Sumo
def lookup(objectId,objectType = 'run'):
    client = boto3.client('inspector')
    finalObj = None

    objectMap = resourceMap.get(objectType)
    if (objectMap is None):
        resourceMap[objectType]= objectMap = {}
    try:
        if (objectType=='run'):
            run = objectMap.get(objectId)
            if (run is None):
                runs = client.describe_assessment_runs(assessmentRunArns=[objectId])
                if (runs is not None):
                    run = runs['assessmentRuns'][0]
                    # For run item, we only collect important properties
                    objectMap[objectId] = finalObj = {'name':run['name'],'createdAt':'%s' % run['createdAt'], 'state':run['state'],'durationInSeconds':run['durationInSeconds'],'startedAt':'%s' % run['startedAt'],'assessmentTemplateArn':run['assessmentTemplateArn']}
            else:
                finalObj = run
        elif (objectType=='template'):
            template = objectMap.get(objectId)
            if (template is None):
                templates = client.describe_assessment_templates(assessmentTemplateArns=[objectId])
                if (templates is not None):
                    finalObj = objectMap[objectId] =  templates['assessmentTemplates'][0]
            else:
                finalObj = template
        elif (objectType=='rulesPackage'):
            rulesPackage = objectMap.get(objectId)
            if (rulesPackage is None):
                rulesPackages = client.describe_rules_packages(rulesPackageArns=[objectId])
                if (rulesPackages is not None):
                    finalObj = objectMap[objectId] =  rulesPackages['rulesPackages'][0]
            else:
                finalObj = rulesPackage
        elif (objectType=='target'):
            target = objectMap.get(objectId)
            if (target is None):
                targets = client.describe_assessment_targets(assessmentTargetArns=[objectId])
                if (targets is not None):
                    finalObj = objectMap[objectId] = targets['assessmentTargets'][0]
            else:
                finalObj = target
        elif (objectType == 'finding'):
            finding = objectMap.get(objectId)
            if (finding is None):
                findings = client.describe_findings(findingArns=[objectId])
                if (findings is not None):
                    finalObj = objectMap[objectId] = findings['findings'][0]
            else:
                finalObj = finding
    except Exception as e:
        logger.error(e)
        raise
    return finalObj

# simple utility function to deserialize datetime objects
def json_deserializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
    elif isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    # Let the base class default method raise the TypeError
    return json.JSONEncoder.default(self, obj)


def sumo_inspector_handler(event, context):
    if ('Records' in event):
        for record in event['Records']:
            # get actual SNS message
            snsObj = record['Sns']
            dataObj = {'Timestamp':snsObj['Timestamp'],'Message':snsObj['Message'],'MessageId':snsObj['MessageId']}
            msgObj = json.loads(snsObj['Message'])
            if (contextLookup):
                # do reverse lookup of each of the following items in Message: target, run, template.
                if ('template' in msgObj):
                    lookupItem = lookup(msgObj['template'],'template')
                    if (lookupItem is not None):
                        logger.info("Got a template item back")
                        msgObj['templateLookup']= lookupItem
                    else:
                        print("Could not lookup template: %s" % msgObj['template'])
                if ('run' in msgObj):
                    lookupItem = lookup(msgObj['run'],'run')
                    if (lookupItem is not None):
                        msgObj['runLookup']= lookupItem
                    else:
                        logger.info("Could not lookup run: %s" % msgObj['run'])
                if ('target' in msgObj):
                    lookupItem = lookup(msgObj['target'],'target')
                    if (lookupItem is not None):
                        msgObj['targetLookup']= lookupItem
                    else:
                        logger.info("Could not lookup target: %s" % msgObj['target'])
            if ('finding' in msgObj):
                # now query findings
                finding = lookup(msgObj['finding'],'finding')
                if (finding is not None):

                    # now query rulesPackage inside the finding
                    rulesPackage = lookup(finding['serviceAttributes']['rulesPackageArn'],'rulesPackage')
                    if (rulesPackage is not None):
                        finding['rulesPackageLookup'] = rulesPackage
                    else:
                        logger.info("Cannot lookup rulesPackageArn: %s"% finding['serviceAttributes']['rulesPackageArn'])
                msgObj['findingDetails'] = finding
             # construct final data object
            dataObj = {'Timestamp':snsObj['Timestamp'],'Message':msgObj,'MessageId':snsObj['MessageId']}

            # now send this object to Sumo side
            rs = sendSumo(json.dumps(dataObj,default=json_deserializer),toCompress=True)

            if (rs[0]!=200):
                logger.info('Error sending data to sumo with code: %d and message: %s '% (rs[0],rs[1]))
                logger.info(json.dumps(dataObj,default=json_deserializer))
            else:
                logger.info("Sent data to Sumo successfully")
    else:
        logger.info('Unrecoganized data')

