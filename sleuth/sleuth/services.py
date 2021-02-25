import json
import logging
import os

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
    keys = []
    key_info = IAM.list_access_keys(UserName=user.username)
    for k in key_info['AccessKeyMetadata']:
        access_date=IAM.get_access_key_last_used(AccessKeyId=k['AccessKeyId'])
        keys.append(Key(k['UserName'],
                        k['AccessKeyId'],
                        k['Status'],
                        k['CreateDate'],
                        access_date['AccessKeyLastUsed']['LastUsedDate'] if 'LastUsedDate' in access_date['AccessKeyLastUsed'] else k['CreateDate']))

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
            if 'KeyAutoExpire' not in tags:
                tags['KeyAutoExpire'] = True
            user = User(u['UserId'], u['UserName'], tags['Slack'], tags['KeyAutoExpire'])
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
    if os.environ.get('DEBUG', False):
        LOGGER.info('Disabling key {} for User {}'.format(key.key_id, username))
    IAM.update_access_key(UserName=key.username,
                          AccessKeyId=key.key_id,
                          Status='Inactive')


def get_ssm_value(ssm_path):
    """Get SSM Parameter value

    Parameters:
    ssm_path (str): Path of the parameter to return

    Returns:
    str: Value of parameter
    """
    resp = SSM.get_parameter(Name=ssm_path,
                             WithDecryption=True)
    return resp['Parameter']['Value']


def send_sns_message(topic_arn, payload):
    """Send SNS message
    """

    if os.environ.get('DEBUG', False):
        print(payload)

    payload = json.dumps(payload)

    resp = SNS.publish(
        TopicArn=topic_arn,
        Message=payload,
        Subject='IAM Sleuth Bot'
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


def prepare_sns_message(users, title, addltext):
    """Prepares message for sending via SNS topic (plain text)

    Parameters:
    users (list): Users with slack and key info attached to user object
    title (str): Title of the message
    addltext (str): Additional text such as further instructions etc

    Returns:
    bool: True if slack send, false if not
    dict: Message prepared for slack API
    """
    msgs = []
    for u in users:
        for k in u.keys:
            if k.audit_state == 'old':
                msgs.append('{}\'s key expires in {} days.'.format(u.username, k.valid_for))

            if k.audit_state == 'expire':
                msgs.append('{}\'s key is disabled.'.format(u.username))

    msg = '{}:\n{}\n{}'.format(title, addltext, "\n".join(msgs))

    send_to_slack = False
    if len(msgs) > 0:
        send_to_slack = True

    if os.environ.get('DEBUG', False):
        print(msg)

    return send_to_slack, msg

def prepare_slack_message(users, title, addltext):
    """Prepares message for sending via Slack webhook

    Parameters:
    users (list): Users with slack and key info attached to user object
    title (str): Title of the message
    addltext (str): Additional text such as further instructions etc

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

    main_attachment = {
        "title": title,
        "text": addltext
    }


    # include master one
    msg = {
        "attachments": []
    }

    send_to_slack = False

    # lets add the notif text
    msg['attachments'].append(main_attachment)

    # only add the attachments that have users
    if len(old_msgs) > 0:
        msg['attachments'].append(old_attachment)
        send_to_slack = True

    if len(expired_msgs) > 0:
        msg['attachments'].append(expired_attachment)
        send_to_slack = True


    if os.environ.get('DEBUG', False):
        print(msg)

    return send_to_slack, msg
