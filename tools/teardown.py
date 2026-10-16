"""Teardown for Dec 4, 2026 (judging closes Nov 20, winners Dec 3). Releases every paid
AWS resource Watermark created and sweeps every region for orphans. Dry run by default:
it prints what it would do. Run with --apply to do it.

    py tools/teardown.py            # list everything that would be removed
    py tools/teardown.py --apply    # remove it

Releases rather than stops: a stopped instance still bills for its disk. Afterwards,
by hand: revoke the `watermark` IAM user's access key, rotate the Ring client secret and
the ngrok authtoken, and move the live link to a static archive page (see README).
"""
from __future__ import annotations

import argparse

import boto3

TAG = ("project", "watermark")
BUCKET = "watermark-evidence-441138556603"
IOT_THING, IOT_POLICY = "rover-1", "watermark-rover-1"
KEY_PAIR, SECURITY_GROUP = "watermark-demo", "watermark-demo"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    act = "REMOVE" if a.apply else "would remove"
    regions = [r["RegionName"] for r in boto3.client("ec2", region_name="us-east-1").describe_regions()["Regions"]]

    for region in regions:
        ec2 = boto3.client("ec2", region_name=region)
        tagged = ec2.describe_instances(Filters=[{"Name": f"tag:{TAG[0]}", "Values": [TAG[1]]},
                                                 {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}])
        ids = [i["InstanceId"] for r in tagged["Reservations"] for i in r["Instances"]]
        if ids:
            print(f"{region}: {act} instances {ids}")
            if a.apply:
                ec2.terminate_instances(InstanceIds=ids)
                ec2.get_waiter("instance_terminated").wait(InstanceIds=ids)
        # Orphans that instance termination does not take with it.
        for v in ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])["Volumes"]:
            print(f"{region}: {act} unattached volume {v['VolumeId']} ({v['Size']} GB)")
            if a.apply:
                ec2.delete_volume(VolumeId=v["VolumeId"])
        for s in ec2.describe_snapshots(OwnerIds=["self"])["Snapshots"]:
            print(f"{region}: {act} snapshot {s['SnapshotId']}")
            if a.apply:
                ec2.delete_snapshot(SnapshotId=s["SnapshotId"])
        for img in ec2.describe_images(Owners=["self"])["Images"]:
            print(f"{region}: {act} image {img['ImageId']}")
            if a.apply:
                ec2.deregister_image(ImageId=img["ImageId"])
        for addr in ec2.describe_addresses()["Addresses"]:
            print(f"{region}: {act} elastic IP {addr.get('PublicIp')}")
            if a.apply:
                ec2.release_address(AllocationId=addr["AllocationId"])
        for gw in ec2.describe_nat_gateways(Filter=[{"Name": "state", "Values": ["available", "pending"]}])["NatGateways"]:
            print(f"{region}: {act} NAT gateway {gw['NatGatewayId']}")
            if a.apply:
                ec2.delete_nat_gateway(NatGatewayId=gw["NatGatewayId"])
        if region == "us-east-1":
            for kp in ec2.describe_key_pairs(Filters=[{"Name": "key-name", "Values": [KEY_PAIR]}])["KeyPairs"]:
                print(f"{region}: {act} key pair {kp['KeyName']}")
                if a.apply:
                    ec2.delete_key_pair(KeyName=KEY_PAIR)
            for sg in ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [SECURITY_GROUP]}])["SecurityGroups"]:
                print(f"{region}: {act} security group {sg['GroupId']}")
                if a.apply:
                    ec2.delete_security_group(GroupId=sg["GroupId"])

    iot = boto3.client("iot", region_name="us-east-1")
    try:
        for principal in iot.list_thing_principals(thingName=IOT_THING)["principals"]:
            cert_id = principal.split("/")[-1]
            print(f"iot: {act} certificate {cert_id[:12]}... and thing {IOT_THING}")
            if a.apply:
                iot.detach_thing_principal(thingName=IOT_THING, principal=principal)
                iot.detach_policy(policyName=IOT_POLICY, target=principal)
                iot.update_certificate(certificateId=cert_id, newStatus="INACTIVE")
                iot.delete_certificate(certificateId=cert_id)
        if a.apply:
            iot.delete_thing(thingName=IOT_THING)
            iot.delete_policy(policyName=IOT_POLICY)
    except iot.exceptions.ResourceNotFoundException:
        print("iot: nothing left")

    s3 = boto3.resource("s3")
    bucket = s3.Bucket(BUCKET)
    try:
        n = sum(1 for _ in bucket.objects.all())
        print(f"s3: {act} bucket {BUCKET} ({n} objects)")
        if a.apply:
            bucket.objects.all().delete()
            bucket.delete()
    except Exception as e:  # noqa: BLE001
        print(f"s3: {BUCKET} not found or not accessible ({type(e).__name__})")

    print("\nBy hand afterwards: deactivate the watermark IAM access key, rotate the Ring client "
          "secret and the ngrok authtoken, and publish the archive page.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
