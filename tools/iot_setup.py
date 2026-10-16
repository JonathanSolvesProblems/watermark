"""Create the rover's AWS IoT Core identity: a Thing, an X.509 certificate and a least-
privilege policy (connect as the rover, subscribe to and receive only its own command
topic). Writes the certificate, key and Amazon root CA to tmp/iot/, which git ignores.
Idempotent: re-running reuses the Thing and policy and only makes a certificate once.

    py tools/iot_setup.py [--rover-id rover-1] [--region us-east-1]
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import boto3

ROOT_CA = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rover-id", default="rover-1")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--prefix", default="watermark/rover")
    a = ap.parse_args()
    iot = boto3.client("iot", region_name=a.region)
    account = boto3.client("sts").get_caller_identity()["Account"]
    out = Path(__file__).resolve().parent.parent / "tmp" / "iot"
    out.mkdir(parents=True, exist_ok=True)

    thing = a.rover_id
    try:
        iot.describe_thing(thingName=thing)
    except iot.exceptions.ResourceNotFoundException:
        iot.create_thing(thingName=thing)

    arn = f"arn:aws:iot:{a.region}:{account}"
    topic = f"{a.prefix}/{a.rover_id}/commands"
    policy_name = f"watermark-{a.rover_id}"
    doc = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": "iot:Connect", "Resource": f"{arn}:client/{a.rover_id}"},
        {"Effect": "Allow", "Action": "iot:Subscribe", "Resource": f"{arn}:topicfilter/{topic}"},
        {"Effect": "Allow", "Action": "iot:Receive", "Resource": f"{arn}:topic/{topic}"},
    ]}
    try:
        iot.get_policy(policyName=policy_name)
    except iot.exceptions.ResourceNotFoundException:
        iot.create_policy(policyName=policy_name, policyDocument=json.dumps(doc))

    cert_file = out / f"{a.rover_id}.cert.pem"
    if not cert_file.exists():
        c = iot.create_keys_and_certificate(setAsActive=True)
        cert_file.write_text(c["certificatePem"], encoding="utf-8")
        (out / f"{a.rover_id}.private.key").write_text(c["keyPair"]["PrivateKey"], encoding="utf-8")
        (out / f"{a.rover_id}.cert.arn").write_text(c["certificateArn"], encoding="utf-8")
        iot.attach_policy(policyName=policy_name, target=c["certificateArn"])
        iot.attach_thing_principal(thingName=thing, principal=c["certificateArn"])
    with urllib.request.urlopen(ROOT_CA, timeout=30) as r:
        (out / "AmazonRootCA1.pem").write_bytes(r.read())

    endpoint = iot.describe_endpoint(endpointType="iot:Data-ATS")["endpointAddress"]
    principals = iot.list_thing_principals(thingName=thing)["principals"]
    print(json.dumps({"thing": thing, "topic": topic, "endpoint": endpoint, "policy": policy_name,
                      "certificates_on_thing": len(principals), "files": sorted(p.name for p in out.iterdir())}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
