#!/usr/bin/env python3

import boto3
import os


# ===============================================================================
def lambda_handler(event, context):
    # Identify AMIs currently running
    instance_amis = get_instance_amis()

    # Identify AMIs in launch configs
    launch_config_amis = get_launch_config_amis()

    # Some random AMIs for testing purposes
    random_amis = set()

    all_amis = set(instance_amis.union(launch_config_amis.union(random_amis)))

    # print(all_amis)

    missing_amis = identify_deleted_amis(all_amis)
    # print(missing_amis)
    print(len(missing_amis))

    if len(missing_amis) > 0:
        message = "The following AMIs are identified as being used but no longer available: {}".format(missing_amis)

        boto3.client('sns').publish(
            TargetArn=os.environ['sns_topic_arn'],
            Message=message,
            Subject="Lambda Monitor: Missing AMIs"
        )


def get_instance_amis():
    instance_amis = set()
    ec2client = boto3.client('ec2')

    # Get first set of instances

    response = ec2client.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'pending', 'running', 'shutting-down', 'stopping', 'stopped'
                ]
            }
        ]
    )
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            # print(instance["ImageId"])
            instance_amis.add(instance["ImageId"])

    # Now check and iterate over all sets of instances
    if 'NextToken' in response:
        while True:
            response = ec2client.describe_instances(
                Filters=[
                    {
                        'Name': 'instance-state-name',
                        'Values': [
                            'pending', 'running', 'shutting-down', 'stopping', 'stopped'
                        ]
                    }
                ],
                NextToken=response['NextToken']
            )
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_amis.add(instance["ImageId"])
            if 'NextToken' not in response:
                break

    return instance_amis


def get_launch_config_amis():
    launch_config_amis = set()
    asgclient = boto3.client('autoscaling')

    # Get first set of launch configurations
    response = asgclient.describe_launch_configurations()
    for launch_config in response["LaunchConfigurations"]:
        # print(launch_config["ImageId"])
        launch_config_amis.add(launch_config["ImageId"])

    # Now check and iterate over all sets of launch configurations
    if 'NextToken' in response:
        while True:
            response = asgclient.describe_launch_configurations(NextToken=response['NextToken'])
            for launch_config in response["LaunchConfigurations"]:
                # print(launch_config["ImageId"])
                launch_config_amis.add(launch_config["ImageId"])
            if 'NextToken' not in response:
                break

    return launch_config_amis


def identify_deleted_amis(ami_set):
    ami_list = list(ami_set)  # Need to use a list so there is an order and can delete items.
    available_amis = set()
    ec2client = boto3.client('ec2')

    # Undocumented limit of 200 AMI's at a time for describe_images()
    while len(ami_list) > 200:
        sub_ami_list = ami_list[:200]
        del ami_list[:200]

        response = ec2client.describe_images(
            Filters=[
                {
                    'Name': 'image-id',
                    'Values': sub_ami_list
                }
            ]
        )
        for image in response['Images']:
            if image['State'] == 'available':
                available_amis.add(image['ImageId'])

    # Now get the last set of AMIs
    response = ec2client.describe_images(
        Filters=[
            {
                'Name': 'image-id',
                'Values': ami_list
            }
        ]
    )
    for image in response['Images']:
        if image['State'] == 'available':
            available_amis.add(image['ImageId'])

    # print("Available AMIs:", available_amis)
    # print("Missing AMIs:", ami_set.difference(available_amis))
    return (ami_set.difference(available_amis))


if __name__ == "__main__":
    lambda_handler("foo", "bar")
