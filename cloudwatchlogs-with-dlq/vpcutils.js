var find = require('lodash').find;
var EC2 = require('aws-sdk/clients/ec2');
var jmespath = require('jmespath');
var ec2 = null;
/*
VPC Log Format
version         The VPC Flow Logs version.
account-id      The AWS account ID for the flow log.
interface-id    The ID of the network interface for which the traffic is recorded.
srcaddr         The source IPv4 or IPv6 address.
dstaddr         The destination IPv4 or IPv6 address.
srcport         The source port of the traffic.
dstport         The destination port of the traffic.
protocol        The IANA protocol number of the traffic. For more information, see Assigned Internet Protocol Numbers.
packets         The number of packets transferred during the capture window.
bytes           The number of bytes transferred during the capture window.
start           The time, in Unix seconds, of the start of the capture window.
end             The time, in Unix seconds, of the end of the capture window.
action          The action associated with the traffic:
                ACCEPT: The recorded traffic was permitted by the security groups or network ACLs.
                REJECT: The recorded traffic was not permitted by the security groups or network ACLs.
log-status      The logging status of the flow log:
                OK: Data is logging normally to the chosen destinations.
                NODATA: There was no network traffic to or from the network interface during the capture window.
                SKIPDATA: Some flow log records were skipped during the capture window. This may be because of an internal capacity constraint, or an internal error.
*/

function discardInternalTraffic(vpcCIDRPrefix, records) {
    if (!vpcCIDRPrefix) {
        return records;
    }
    var filteredRecords = [];
    records.forEach(function (log) {
        var vpcMessage = log.message.split(" ");
        var srcaddr = vpcMessage[3];
        var dstaddr = vpcMessage[4];
        var vpcCIDRPrefixes = vpcCIDRPrefix.split(",").map((x) => x.trim()).filter((x) => x);
        var isSrcIPinternal = vpcCIDRPrefixes.reduce((r, v) => r || srcaddr.startsWith(v), false);
        var isDstIPinternal = vpcCIDRPrefixes.reduce((r, v) => r || dstaddr.startsWith(v), false);
        if (!(isSrcIPinternal && isDstIPinternal)) {
            filteredRecords.push(log);
        }
    });
    return filteredRecords;
}


/**
 * Describes the Network Interfaces associated with this account.
 *
 * @return `Promise` for async processing
 */
function listNetworkInterfaces(allIPaddresses) {
    if (!ec2) {
        ec2 = new EC2({region: process.env.AWS_REGION});
    }
    var params = {
        Filters: [
            {
              Name: 'private-ip-address',
              Values: allIPaddresses
            }
        ]
    }
    return ec2.describeNetworkInterfaces(params).promise();
}

/**
 * Builds a listing of Elastic Network Interfaces (ENI) associated with this account and
 * returns an Object representing that ENI, specifically its unique identifier, associated
 * security groups, and primary private IP address.
 *
 * Per AWS documentation, we only capture the primary, private IPv4 address of the ENI:
 *
 * - If your network interface has multiple IPv4 addresses and traffic is sent to a secondary private IPv4
 *   address, the flow log displays the primary private IPv4 address in the destination IP address field.
 * - In the case of both `srcaddr` and `dstaddr` in VPC Flow Logs: the IPv4 address of the network interface
 *   is always its private IPv4 address.
 *
 * @see http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/flow-logs.html
 *
 * Returns structure like:
 *  [
 *    { interfaceId: 'eni-c1a7da8c',
 *      securityGroupIds: [ 'sg-b2b454d4' ],
 *      ipAddress: '10.0.1.24' },
 *    { interfaceId: 'eni-03cbb94e',
 *      securityGroupIds: [ 'sg-a3b252c5' ]
 *      ipAddress: '10.0.2.33'}
 *    ...
 *  ]
 */
function buildEniToSecurityGroupMapping(allIPaddresses) {
    //console.log(allIPaddresses.length + " ip addresses found in logs");
    return listNetworkInterfaces(allIPaddresses).then(function (interfaces) {
        console.log(interfaces["NetworkInterfaces"].length + " Interfaces Fetched");
        return jmespath.search(interfaces,
            `NetworkInterfaces[].{
              interfaceId: NetworkInterfaceId,
              securityGroupIds: Groups[].GroupId,
              ipAddress: PrivateIpAddresses[?Primary].PrivateIpAddress,
              subnetId: SubnetId,
              vpcId: VpcId
            }`);
    });
}
//filter on interfaceID
function includeSecurityGroupIds(records) {
    var allIPaddresses = [];
    records.forEach(function(log) {
        var vpcMessage = log.message.split(" ");
        allIPaddresses.push(vpcMessage[3]);
        allIPaddresses.push(vpcMessage[4]);
    });
    allIPaddresses = Array.from(new Set(allIPaddresses));
    return buildEniToSecurityGroupMapping(allIPaddresses).then(function (mapping) {
        records.forEach(function (log) {
            var vpcMessage = log.message.split(" ");
            var eniData = find(mapping, {'interfaceId': vpcMessage[2]});
            if (eniData && eniData.ipAddress.length > 0) {
                log['security-group-ids'] = eniData.securityGroupIds;
                if (vpcMessage[4] === eniData.ipAddress[0]) {
                    // destination matches eni's privateIP
                    var srcEniData = find(mapping, {'ipAddress': vpcMessage[3]});
                    log['direction'] = (srcEniData && (srcEniData.subnetId == eniData.subnetId) ? "internal" : "inbound");
                } else {
                    // sources matches eni's privateIP
                    var destEniData = find(mapping, {'ipAddress': vpcMessage[4]});
                    log['direction'] = (destEniData && (destEniData.subnetId == eniData.subnetId) ? "internal" : "outbound");
                }
                log['subnet-id'] = eniData.subnetId;
                log['vpc-id'] = eniData.vpcId;
                log['aws-region'] = process.env.AWS_REGION;
            } else {
                console.log(`No ENI data found for interface ${vpcMessage[2]}`);
            }
        });
        return records;
    }).catch(function (err) {
        console.log("Error in includeSecurityGroupIds", err);
        return records;
    });
}

module.exports = {
    discardInternalTraffic: discardInternalTraffic,
    includeSecurityGroupIds: includeSecurityGroupIds
};
