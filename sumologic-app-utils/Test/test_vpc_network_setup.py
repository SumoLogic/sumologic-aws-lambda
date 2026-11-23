import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
sys.path.insert(0, sys.argv.pop(1))

import boto3
from moto import mock_aws

STACK = "arn:aws:cloudformation:us-east-1:123456789012:stack/net/abc"
PHYSICAL = "VPCNetworkSetup/vpcnet-{}"
PREFIX = "/sumologic/awso/network"


def tags(resource):
    return {t["Key"]: t["Value"] for t in resource.get("Tags", [])}


@mock_aws
class VPCNetworkSetupTest(unittest.TestCase):
    def setUp(self):
        from awsresource import VPCNetworkSetup, ElasticIPLookup
        self.cls, self.eip_cls = VPCNetworkSetup, ElasticIPLookup
        self.ec2 = boto3.client("ec2", region_name="us-east-1")
        self.ssm = boto3.client("ssm", region_name="us-east-1")
        self.vpc = self.ec2.create_vpc(CidrBlock="10.0.0.0/24")["Vpc"]["VpcId"]
        self.res = self.cls({})
        # NAT waiter is not needed against moto
        self.res.ec2_client.get_waiter = mock.MagicMock()

    def build_full_network(self):
        igw = self.ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
        self.ec2.attach_internet_gateway(InternetGatewayId=igw, VpcId=self.vpc)
        pub = self.ec2.create_subnet(VpcId=self.vpc, CidrBlock="10.0.0.0/26", AvailabilityZone="us-east-1a")["Subnet"]["SubnetId"]
        prt = self.ec2.create_route_table(VpcId=self.vpc)["RouteTable"]["RouteTableId"]
        self.ec2.create_route(RouteTableId=prt, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw)
        self.ec2.associate_route_table(RouteTableId=prt, SubnetId=pub)
        alloc = self.ec2.allocate_address(Domain="vpc")
        nat = self.ec2.create_nat_gateway(SubnetId=pub, AllocationId=alloc["AllocationId"])["NatGateway"]["NatGatewayId"]
        priv = self.ec2.create_subnet(VpcId=self.vpc, CidrBlock="10.0.0.64/26", AvailabilityZone="us-east-1b")["Subnet"]["SubnetId"]
        rt = self.ec2.create_route_table(VpcId=self.vpc)["RouteTable"]["RouteTableId"]
        self.ec2.create_route(RouteTableId=rt, DestinationCidrBlock="0.0.0.0/0", NatGatewayId=nat)
        self.ec2.associate_route_table(RouteTableId=rt, SubnetId=priv)
        return priv, alloc["PublicIp"], pub

    def owned(self, kind):
        filters = [{"Name": "tag:CreatedBy", "Values": ["sumologic-awso"]}]
        items = {
            "subnet": lambda: self.ec2.describe_subnets(Filters=filters)["Subnets"],
            "igw": lambda: self.ec2.describe_internet_gateways(Filters=filters)["InternetGateways"],
            "rt": lambda: self.ec2.describe_route_tables(Filters=filters)["RouteTables"],
            "eip": lambda: self.ec2.describe_addresses(Filters=filters)["Addresses"],
            "nat": lambda: [n for n in self.ec2.describe_nat_gateways(Filters=filters)["NatGateways"] if n["State"] != "deleted"],
            "sg": lambda: self.ec2.describe_security_groups(Filters=filters)["SecurityGroups"],
        }[kind]()
        # moto ignores tag filters on describe_nat_gateways, so check tags here as well
        return [r for r in items if tags(r).get("CreatedBy") == "sumologic-awso"]

    def test_full_vpc_creates_nothing(self):
        priv, ip, _ = self.build_full_network()
        data, pid = self.res.create(self.vpc, "", [], STACK)
        self.assertEqual(data["SubnetIds"], priv)
        self.assertEqual(data["NatPublicIp"], ip)
        self.assertEqual(pid, f"vpcnet-{self.vpc}")
        for kind in ("subnet", "igw", "rt", "eip", "nat"):
            self.assertEqual(self.owned(kind), [], kind)

    def test_delete_never_touches_customer_nat(self):
        self.build_full_network()
        self.res.create(self.vpc, "", [], STACK)
        self.res._wait_nat_deleted = lambda ids, timeout=600: None
        self.res.delete(STACK, physical_id=PHYSICAL.format(self.vpc))
        nats = [n for n in self.ec2.describe_nat_gateways()["NatGateways"] if n["State"] == "available"]
        self.assertEqual(len(nats), 1)
        self.assertEqual(len(self.ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [self.vpc]}])["Subnets"]), 2)

    def test_given_subnet_validated(self):
        priv, ip, _ = self.build_full_network()
        data, _ = self.res.create(self.vpc, "", [priv], STACK)
        self.assertEqual((data["SubnetIds"], data["NatPublicIp"], data["VpcId"]), (priv, ip, self.vpc))

    def test_given_subnet_without_nat_route_fails(self):
        _, _, pub = self.build_full_network()
        with self.assertRaisesRegex(Exception, f"Subnet {pub} does not route 0.0.0.0/0 to a NAT"):
            self.res.create(self.vpc, "", [pub], STACK)

    def test_bare_vpc_creates_all_then_delete_removes_only_owned(self):
        customer_subnet = self.ec2.create_subnet(VpcId=self.vpc, CidrBlock="10.0.0.0/28")["Subnet"]["SubnetId"]
        data, _ = self.res.create(self.vpc, "", [], STACK)
        subnets = data["SubnetIds"].split(",")
        self.assertEqual(len(subnets), 2)
        self.assertTrue(data["NatPublicIp"])
        self.assertEqual(len(self.owned("igw")), 1)
        self.assertEqual(len(self.owned("nat")), 1)
        self.assertEqual(len(self.owned("eip")), 1)
        self.assertEqual(len(self.owned("subnet")), 3)  # public + 2 private
        self.assertEqual(len(self.owned("sg")), 1)
        self.assertEqual(data["SecurityGroupId"], self.owned("sg")[0]["GroupId"])
        for s in self.owned("subnet"):
            self.assertEqual(tags(s)["SumoStackId"], STACK)
            self.assertNotEqual(s["CidrBlock"], "10.0.0.0/28")

        # Idempotent re-run (update for same VPC) creates nothing new.
        data2, _ = self.res.update(self.vpc, "", [], STACK)
        self.assertEqual(set(data2["SubnetIds"].split(",")), set(subnets))
        self.assertEqual(len(self.owned("subnet")), 3)
        self.assertEqual(len(self.owned("sg")), 1)
        self.assertEqual(data2["SecurityGroupId"], data["SecurityGroupId"])

        self.res._wait_nat_deleted = lambda ids, timeout=600: None
        self.res.delete(STACK, physical_id=PHYSICAL.format(self.vpc))
        for kind in ("subnet", "igw", "rt", "eip", "nat", "sg"):
            self.assertEqual(self.owned(kind), [], kind)
        remaining = [s["SubnetId"] for s in self.ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [self.vpc]}])["Subnets"]]
        self.assertEqual(remaining, [customer_subnet])

    def test_provided_eip_is_used_and_not_released(self):
        alloc = self.ec2.allocate_address(Domain="vpc")
        data, _ = self.res.create(self.vpc, alloc["AllocationId"], [], STACK)
        self.assertEqual(data["NatPublicIp"], alloc["PublicIp"])
        self.assertEqual(self.owned("eip"), [])
        self.res._wait_nat_deleted = lambda ids, timeout=600: None
        self.res.delete(STACK, physical_id=PHYSICAL.format(self.vpc))
        self.assertEqual(len(self.ec2.describe_addresses(AllocationIds=[alloc["AllocationId"]])["Addresses"]), 1)

    def test_no_free_cidr_fails(self):
        self.ec2.create_subnet(VpcId=self.vpc, CidrBlock="10.0.0.0/24")
        with self.assertRaisesRegex(Exception, "does not have 1 free /28"):
            self.res.create(self.vpc, "", [], STACK)

    def test_extract_params(self):
        params = self.res.extract_params({"RequestType": "Create", "ResourceProperties": {
            "VpcId": self.vpc, "ElasticIPAllocationId": "", "PrivateSubnetIds": " subnet-1, ,subnet-2", "StackId": STACK,
            "SSMPrefix": PREFIX}})
        self.assertEqual(params["ssm_prefix"], PREFIX)
        self.assertEqual(params["private_subnet_ids"], ["subnet-1", "subnet-2"])
        self.assertEqual(self.res.extract_params({"RequestType": "Update", "ResourceProperties": {"PrivateSubnetIds": ""}})["private_subnet_ids"], [])
        delete_params = self.res.extract_params({"RequestType": "Delete", "PhysicalResourceId": PHYSICAL.format(self.vpc),
                                                 "ResourceProperties": {"StackId": STACK}})
        self.assertEqual(delete_params["physical_id"], PHYSICAL.format(self.vpc))
        self.assertNotIn("private_subnet_ids", delete_params)

    # ---------- SSM inputs under /sumologic/awso/network ----------
    def put_input(self, name, value, type_="String"):
        self.ssm.put_parameter(Name=f"{PREFIX}/{name}", Value=value, Type=type_)

    def ssm_value(self, name):
        try:
            return self.ssm.get_parameter(Name=f"{PREFIX}/{name}")["Parameter"]["Value"]
        except self.ssm.exceptions.ParameterNotFound:
            return None

    def test_only_vpc_id_in_ssm_creates_everything_and_keeps_input(self):
        self.put_input("vpc-id", self.vpc)
        data, pid = self.res.create("", "", [], STACK, PREFIX)
        self.assertEqual(data["VpcId"], self.vpc)
        self.assertEqual(pid, f"vpcnet-{self.vpc}")
        self.assertEqual(len(self.owned("sg")), 1)
        self.assertEqual(len(self.owned("nat")), 1)
        # outputs written, including the customer's own vpc-id which must stay untouched and untagged
        self.assertEqual(self.ssm_value("nat-public-ip"), data["NatPublicIp"])
        self.assertEqual(self.ssm_value("private-subnet-ids"), data["SubnetIds"])
        self.assertEqual(self.ssm_value("security-group-id"), data["SecurityGroupId"])
        self.assertFalse(self.res._is_stack_written(f"{PREFIX}/vpc-id"))
        self.assertTrue(self.res._is_stack_written(f"{PREFIX}/nat-public-ip", STACK, self.vpc))

        # rerun (stack update) must not treat its own tagged output as customer input
        data2, _ = self.res.update("", "", [], STACK, PREFIX)
        self.assertEqual(data2["SecurityGroupId"], data["SecurityGroupId"])
        self.assertEqual(len(self.owned("sg")), 1)

        self.res._wait_nat_deleted = lambda ids, timeout=600: None
        self.res.delete(STACK, physical_id=PHYSICAL.format(self.vpc), ssm_prefix=PREFIX)
        for kind in ("subnet", "igw", "rt", "eip", "nat", "sg"):
            self.assertEqual(self.owned(kind), [], kind)
        self.assertEqual(self.ssm_value("vpc-id"), self.vpc)  # customer input survives
        for name in ("nat-public-ip", "private-subnet-ids", "security-group-id"):
            self.assertIsNone(self.ssm_value(name), name)

    def test_all_inputs_in_ssm_nothing_created(self):
        priv, ip, _ = self.build_full_network()
        sg = self.ec2.create_security_group(GroupName="cust", Description="d", VpcId=self.vpc)["GroupId"]
        self.ec2.authorize_security_group_egress(GroupId=sg, IpPermissions=[{
            "IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        alloc = [a for a in self.ec2.describe_addresses()["Addresses"] if a["PublicIp"] == ip][0]["AllocationId"]
        self.put_input("vpc-id", self.vpc)
        self.put_input("private-subnet-ids", priv, "StringList")
        self.put_input("elastic-ip-allocation-id", alloc)
        self.put_input("security-group-id", sg)
        data, _ = self.res.create("", "", [], STACK, PREFIX)
        self.assertEqual((data["SubnetIds"], data["SecurityGroupId"], data["NatPublicIp"]), (priv, sg, ip))
        for kind in ("subnet", "igw", "rt", "eip", "nat", "sg"):
            self.assertEqual(self.owned(kind), [], kind)
        self.assertEqual(self.ssm_value("nat-public-ip"), ip)
        self.assertEqual(self.ssm_value("security-group-id"), sg)  # customer's value, not overwritten

    def test_direct_parameter_beats_ssm(self):
        priv, ip, _ = self.build_full_network()
        other = self.ec2.create_vpc(CidrBlock="10.9.0.0/24")["Vpc"]["VpcId"]
        self.put_input("vpc-id", other)
        data, _ = self.res.create(self.vpc, "", [], STACK, PREFIX)
        self.assertEqual(data["VpcId"], self.vpc)

    def test_vpc_id_missing_fails_with_path(self):
        with self.assertRaisesRegex(Exception, f"{PREFIX}/vpc-id"):
            self.res.create("", "", [], STACK, PREFIX)

    def test_vpc_not_found_and_dns_disabled(self):
        with self.assertRaisesRegex(Exception, "not found"):
            self.res.create("vpc-0123456789abcdef0", "", [], STACK)
        self.ec2.modify_vpc_attribute(VpcId=self.vpc, EnableDnsSupport={"Value": False})
        with self.assertRaisesRegex(Exception, "DNS support disabled"):
            self.res.create(self.vpc, "", [], STACK)

    def test_security_group_validation(self):
        self.build_full_network()
        other = self.ec2.create_vpc(CidrBlock="10.9.0.0/24")["Vpc"]["VpcId"]
        foreign = self.ec2.create_security_group(GroupName="f", Description="d", VpcId=other)["GroupId"]
        self.put_input("vpc-id", self.vpc)
        self.put_input("security-group-id", foreign)
        with self.assertRaisesRegex(Exception, "does not belong to VPC"):
            self.res.create("", "", [], STACK, PREFIX)
        self.ssm.delete_parameter(Name=f"{PREFIX}/security-group-id")

        closed = self.ec2.create_security_group(GroupName="c", Description="d", VpcId=self.vpc)["GroupId"]
        self.ec2.revoke_security_group_egress(GroupId=closed, IpPermissions=[{
            "IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self.put_input("security-group-id", closed)
        with self.assertRaisesRegex(Exception, "does not allow outbound tcp/443"):
            self.res.create("", "", [], STACK, PREFIX)

    def customer_sg(self, vpc):
        group = self.ec2.create_security_group(GroupName=f"cust-{vpc}", Description="d", VpcId=vpc)["GroupId"]
        self.ec2.authorize_security_group_egress(GroupId=group, IpPermissions=[{
            "IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        return group

    def test_direct_security_group_parameter(self):
        priv, ip, _ = self.build_full_network()
        sg = self.customer_sg(self.vpc)
        data, _ = self.res.create(self.vpc, "", [priv], STACK, security_group_id=sg)
        self.assertEqual(data["SecurityGroupId"], sg)
        self.assertEqual(self.owned("sg"), [])
        # a direct group that is in another VPC is rejected, not replaced
        other = self.ec2.create_vpc(CidrBlock="10.9.0.0/24")["Vpc"]["VpcId"]
        with self.assertRaisesRegex(Exception, "does not belong to VPC"):
            self.res.create(self.vpc, "", [priv], STACK, security_group_id=self.customer_sg(other))

    def test_direct_security_group_beats_ssm(self):
        self.build_full_network()
        direct = self.customer_sg(self.vpc)
        self.put_input("vpc-id", self.vpc)
        self.put_input("security-group-id", "sg-0123456789abcdef0")  # would fail validation if it were used
        data, _ = self.res.create("", "", [], STACK, PREFIX, direct)
        self.assertEqual(data["SecurityGroupId"], direct)

    def test_direct_parameters_only_without_ssm(self):
        priv, ip, _ = self.build_full_network()
        sg = self.customer_sg(self.vpc)
        alloc = [a for a in self.ec2.describe_addresses()["Addresses"] if a["PublicIp"] == ip][0]["AllocationId"]
        data, _ = self.res.create(self.vpc, alloc, [priv], STACK, None, sg)
        self.assertEqual((data["SubnetIds"], data["SecurityGroupId"], data["NatPublicIp"]), (priv, sg, ip))
        for kind in ("subnet", "igw", "rt", "eip", "nat", "sg"):
            self.assertEqual(self.owned(kind), [], kind)

    def test_extract_params_security_group(self):
        params = self.res.extract_params({"RequestType": "Create", "ResourceProperties": {
            "VpcId": self.vpc, "SecurityGroupId": "sg-0abc", "StackId": STACK}})
        self.assertEqual(params["security_group_id"], "sg-0abc")

    def test_eip_must_match_existing_nat(self):
        self.build_full_network()
        other = self.ec2.allocate_address(Domain="vpc")["AllocationId"]
        with self.assertRaisesRegex(Exception, "does not belong to NAT gateway"):
            self.res.create(self.vpc, other, [], STACK)
        with self.assertRaisesRegex(Exception, "not found"):
            self.res.create(self.vpc, "eipalloc-0123456789abcdef0", [], STACK)

    def test_delete_without_physical_id_vpc_is_noop(self):
        self.res.delete(STACK, physical_id="VPCNetworkSetup/some-other-id")

    def test_elastic_ip_lookup(self):
        alloc = self.ec2.allocate_address(Domain="vpc")
        data, pid = self.eip_cls({}).create(alloc["AllocationId"])
        self.assertEqual(data, {"PublicIp": alloc["PublicIp"]})
        self.assertEqual(pid, alloc["AllocationId"])


@mock_aws
class NetworkSSMParametersTest(unittest.TestCase):
    NAMES = ("vpc-id", "private-subnet-ids", "security-group-id", "nat-public-ip")

    def setUp(self):
        from awsresource import NetworkSSMParameters
        self.ssm = boto3.client("ssm", region_name="us-east-1")
        self.cfn = boto3.client("cloudformation", region_name="us-east-1")
        self.res = NetworkSSMParameters({})
        self.args = dict(vpc_id="vpc-111", private_subnet_ids="subnet-a,subnet-b", security_group_id="sg-111",
                         nat_public_ip="1.2.3.4", stack_id=STACK, ssm_prefix=PREFIX)

    def put(self, name, value, **tags):
        self.ssm.put_parameter(Name=f"{PREFIX}/{name}", Value=value, Type="String")
        if tags:
            self.ssm.add_tags_to_resource(ResourceType="Parameter", ResourceId=f"{PREFIX}/{name}",
                                          Tags=[{"Key": k, "Value": v} for k, v in tags.items()])

    def value(self, name):
        return self.ssm.get_parameter(Name=f"{PREFIX}/{name}")["Parameter"]["Value"]

    def tags_of(self, name):
        response = self.ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=f"{PREFIX}/{name}")
        return {t["Key"]: t["Value"] for t in response["TagList"]}

    def live_stack(self):
        template = '{"Resources": {"Q": {"Type": "AWS::SQS::Queue"}}}'
        return self.cfn.create_stack(StackName="other-net", TemplateBody=template)["StackId"]

    def test_fresh_create_writes_all_tagged(self):
        data, pid = self.res.create(**self.args)
        self.assertEqual(data, {"NatPublicIp": "1.2.3.4"})
        self.assertEqual(pid, "ssmnet-vpc-111")
        self.assertEqual(self.value("private-subnet-ids"), "subnet-a,subnet-b")
        for name in self.NAMES:
            self.assertEqual(self.tags_of(name), {"CreatedBy": "sumologic-awso", "SumoStackId": STACK, "SumoVpcId": "vpc-111"})

    def test_orphans_and_customer_inputs_are_overwritten(self):
        gone = "arn:aws:cloudformation:us-east-1:123456789012:stack/vpctest/deleted"
        for name in ("private-subnet-ids", "security-group-id", "nat-public-ip"):
            self.put(name, "old", CreatedBy="sumologic-awso", SumoStackId=gone, SumoVpcId="vpc-old")
        self.put("vpc-id", "vpc-old", ManagedBy="sumologic-awso-static-ip-populate")
        self.res.create(**self.args)
        self.assertEqual([self.value(n) for n in self.NAMES], ["vpc-111", "subnet-a,subnet-b", "sg-111", "1.2.3.4"])
        for name in self.NAMES:
            self.assertEqual(self.tags_of(name)["SumoStackId"], STACK)

    def test_parameter_of_live_stack_fails_and_writes_nothing(self):
        other = self.live_stack()
        self.put("vpc-id", "vpc-other")
        self.put("nat-public-ip", "9.9.9.9", CreatedBy="sumologic-awso", SumoStackId=other, SumoVpcId="vpc-other")
        with self.assertRaises(Exception) as ctx:
            self.res.create(**self.args)
        self.assertIn(other, str(ctx.exception))
        self.assertEqual(self.value("vpc-id"), "vpc-other")
        self.assertEqual(self.value("nat-public-ip"), "9.9.9.9")

    def test_update_is_idempotent(self):
        self.res.create(**self.args)
        self.res.update(**dict(self.args, nat_public_ip="5.6.7.8"))
        self.assertEqual(self.value("nat-public-ip"), "5.6.7.8")

    def test_delete_removes_only_own_parameters(self):
        self.res.create(**self.args)
        self.ssm.add_tags_to_resource(ResourceType="Parameter", ResourceId=f"{PREFIX}/vpc-id",
                                      Tags=[{"Key": "SumoStackId", "Value": "arn:other"}])
        self.res.delete(STACK, PREFIX, physical_id="NetworkSSMParameters/ssmnet-vpc-111")
        remaining = [p["Name"] for p in self.ssm.get_parameters_by_path(Path=PREFIX)["Parameters"]]
        self.assertEqual(remaining, [f"{PREFIX}/vpc-id"])

    def test_delete_without_physical_id_is_noop(self):
        self.res.create(**self.args)
        self.res.delete(STACK, PREFIX, physical_id="NetworkSSMParameters/other")
        self.assertEqual(len(self.ssm.get_parameters_by_path(Path=PREFIX)["Parameters"]), 4)

    def test_extract_params(self):
        props = {"StackId": STACK, "SSMPrefix": PREFIX, "VpcId": "vpc-111", "PrivateSubnetIds": "subnet-a,subnet-b",
                 "SecurityGroupId": "sg-111", "NatPublicIp": "1.2.3.4"}
        self.assertEqual(self.res.extract_params({"RequestType": "Create", "ResourceProperties": props}), {
            "stack_id": STACK, "ssm_prefix": PREFIX, "vpc_id": "vpc-111", "private_subnet_ids": "subnet-a,subnet-b",
            "security_group_id": "sg-111", "nat_public_ip": "1.2.3.4"})
        deleted = self.res.extract_params({"RequestType": "Delete", "ResourceProperties": props,
                                           "PhysicalResourceId": "N/ssmnet-vpc-111"})
        self.assertEqual(deleted["physical_id"], "N/ssmnet-vpc-111")


class AllowlistErrorTest(unittest.TestCase):
    def test_allowlist_message(self):
        import requests
        from sumologic import SumoLogic
        r = requests.Response()
        r.status_code = 403
        r._content = b'{"message":"Access is not allowed from this IP address"}'
        r.url = "https://api.sumologic.com/api/v1/collectors"
        with self.assertRaisesRegex(requests.HTTPError, "Sumo Logic API allowlist"):
            SumoLogic._raise_for_status(r)
        r.status_code = 404
        with self.assertRaises(requests.HTTPError) as ctx:
            SumoLogic._raise_for_status(r)
        self.assertNotIn("allowlist", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
