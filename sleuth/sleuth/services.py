import json
import logging

import boto3
import requests

IAM = boto3.client('iam')
SSM = boto3.client('ssm')
SNS = boto3.client('sns')

LOGGER = logging.getLogger('sleuth')

###################
# AWS
###################

def get_iam_key_info(user):
    """Fetches User key info

    Parameters:
    user (str): user to fetch key info for

    Returns:
    list (Key): Return list of keys for a single user
    """
    from sleuth.auditor import Key
    resp = IAM.list_access_keys(UserName=user.username)
    keys = []
    for k in resp['AccessKeyMetadata']:
        keys.append(Key(k['UserName'],
                        k['AccessKeyId'],
                        k['Status'],
                        k['CreateDate']))
    return keys


def get_user_tag(username):
    """Fetches User Tags

    A helper function to unpack the API response in a python friendly way

    Parameters:
    username (str): Username of the user to fetch tags for

    Returns:
    dict: key val of the tags
    """
    resp = IAM.list_user_tags(UserName=username)

    tags = {}
    for t in resp['Tags']:
        tags[t['Key']] = t['Value']

    return tags


def format_slack_id(slackid, display_name=None):
    """Helper function that formats the slack message to mention a user or group id such as Infra etc

    Parameters:
    slackid (str): User unique id, starts with a 'U', or group unique id starts with a 'subteam'
                   If slackid isn't recognized as user or team ID will return slackid itself as last ditch effort
    display_name (str): Display name to use while slackid is put into '()' so slack still pings. Only used
                        when mentioning teams/groups since the slackid calls out team name instead of IAM account.

    Returns:
    str: The user or team id in a slack mention, example: <@U12345> or <!subteam^T1234>
    """

    if slackid is None or len(slackid) == 0:
        LOGGER.warning('Slack ID is None, which it should not be')
        return 'UNKNOWN'

    if 'subteam' in slackid and '-' in slackid:
        # format and replace "-" with "^" since IAM rules doesn't allow "^"
        if display_name is None:
            return '(see log) <!{}>'.format(slackid).replace('-', '^')
        else:
            return '{} (<!{}>)'.format(display_name, slackid.replace('-', '^'))
    elif slackid[0] == 'U':
        return '<@{}>'.format(slackid)
    else:
        # don't recognize slackid so return as last ditch effort
        LOGGER.warning('Do not know how to format slack id: {} which is not a team or user id'.format(slackid))
        return slackid


def get_iam_users():
    """Fetches IAM users WITH key info

    Parameters:
    None

    Returns:
    list (User): User and related access key info
    """
    from sleuth.auditor import User

    pag = IAM.get_paginator('list_users')
    iter = pag.paginate()

    users = []
    for resp in iter:
        for u in resp['Users']:
            tags = get_user_tag(u['UserName'])
            if 'Slack' not in tags:
                LOGGER.info('IAM User: {} is missing Slack tag!'.format(u['UserName']))
                # since no slack id, lets fill in the username so at least we know the account
                tags['Slack'] = u['UserName']
            user = User(u['UserId'], u['UserName'], tags['Slack'])
            user.keys = get_iam_key_info(user)
            users.append(user)

    return users


def disable_key(key, username):
    """Disables an AWS access key

    Parameters:
    user (str): User ID of key to disable
    key (str): Key ID to disable

    Returns:
    None
    """
    LOGGER.info('Disabling key {} for User {}'.format(key.key_id, username))
    IAM.update_access_key(UserName=key.username,
                          AccessKeyId=key.key_id,
                          Status='Inactive')
    LOGGER.info('Successfully disabled key {} for User {}'.format(key.key_id, username))


def get_ssm_value(ssm_path):
    """Get SSM Parameter value

    Parameters:
    ssm_path (str): Path of the parametere to return

    Returns:
    str: Value of parameter
    """
    resp = SSM.get_parameter(Name=ssm_path,
                             WithDecryption=True)
    return resp['Parameter']['Value']


def send_sns_message(topic_arn, payload):
    """Send SNS message
    """
    print(payload)
    payload = json.dumps(payload)
    print(payload)

    resp = SNS.publish(
        TopicArn=topic_arn,
        Message=payload,
        Subject='IAM Slueth Bot'
    )

    if 'MessageId' in resp:
        LOGGER.info('Message sent successfully sent to SNS {}, msg ID'.format(topic_arn, resp['MessageId']))
    else:
        LOGGER.error('Message could NOT be sent {}'.format(topic_arn))




###################
# Slack
###################
def send_slack_message(webhook, payload):
    LOGGER.info('Calling webhook: {}'.format(webhook[0:15]))

    resp = requests.post(webhook, data=json.dumps(payload),
                         headers={'Content-Type': 'application/json'})

    if resp.status_code == requests.codes.ok:
        LOGGER.info('Successfully posted to slack')
    else:
        msg = 'Unsuccessfully posted to slack, response {}, {}'.format(resp.status_code, resp.text)
        LOGGER.error(msg)


def prepare_sns_message(users):
    """Prepares message for sending via SNS topic (plain text)

    Parameters:
    users (list): Users with slack and key info attached to user object

    Returns:
    bool: True if slack send, false if not
    dict: Message prepared for slack API
    """
    msgs = []
    for u in users:
        for k in u.keys:
            if k.audit_state == 'old':
                msgs.append('{}\'s key expires in {} days.'.format(format_slack_id(u.slack_id, u.username), k.valid_for))

            if k.audit_state == 'expire':
                msgs.append('{}\'s key is disabled.'.format(format_slack_id(u.slack_id, u.username)))


    msg = 'AWS IAM Key report:\n\n{}\n\n How to doc for <https://github.com/transcom/ppp-infra/tree/master/transcom-ppp#rotating-aws-access-keys|key rotation>. TLDR: \n ```cd transcom-ppp\ngit pull && rotate-aws-access-key``` \n\nOnce key is expired will require team Infra involvement to reset key and MFA'.format("\n".join(msgs))

    send_to_slack = False
    if len(msgs) > 0:
        send_to_slack = True

    print(msg)
    return send_to_slack, msg

def prepare_slack_message(users):
    """Prepares message for sending via Slack webhook

    Note: Will not work with SNS sending

    Parameters:
    users (list): Users with slack and key info attached to user object

    Returns:
    bool: True if slack send, false if not
    dict: Message prepared for slack API
    """

    old_msgs = []
    expired_msgs = []
    for u in users:
        for k in u.keys:
            if k.audit_state == 'old':
                old_msgs.append('{}\'s key expires in {} days.'.format(format_slack_id(u.slack_id, u.username),
                                                                       k.valid_for))

            if k.audit_state == 'expire':
                expired_msgs.append('{}\'s key is disabled.'.format(format_slack_id(u.slack_id, u.username)))



    old_attachment = {
        "title": "IAM users with access keys expiring",
        "color": "#ffff00", #yellow
        "fields": [
            {
                "title": "Users",
                "value": "\n".join(old_msgs),
            }
        ]
    }

    expired_attachment = {
        "title": "IAM users with disabled access keys",
        "color": "#ff0000", #red
        "fields": [
            {
                "title": "Users",
                "value": "\n".join(expired_msgs),
            }
        ]
    }

    howto_attachment = {
        "title": "Access Key Rotation Instructions",
        "text": "https://github.com/transcom/ppp-infra/tree/master/transcom-ppp#rotating-aws-access-keys"
    }


    # include master one
    msg = {
        "attachments": []
    }

    send_to_slack = False
    # only add the attachments that have users
    if len(old_msgs) > 0:
        msg['attachments'].append(old_attachment)
        send_to_slack = True

    if len(expired_msgs) > 0:
        msg['attachments'].append(expired_attachment)
        send_to_slack = True

    msg['attachments'].append(howto_attachment)
    return send_to_slack, msg
