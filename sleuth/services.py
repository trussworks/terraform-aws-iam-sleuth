import json
import logging

import boto3
import requests

IAM = boto3.client('iam')
SSM = boto3.client('ssm')

LOGGER = logging.getLogger('sleuth')

# TODO make this load dynamically
SLACK_USERS = {
    'lee': 'UP6A26UAE'
}

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
            user = User(u['UserId'], u['UserName'], find_slack_user(u['UserName']))
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


###################
# Slack
###################
def send_slack_message(payload):
    webhook = get_ssm_value('/integrations/test_general')

    resp = requests.post(webhook, data=json.dumps(payload),
                         headers={'Content-Type': 'application/json'})

    if resp.status_code == requests.codes.ok:
        LOGGER.info('Successfully posted to slack')
    else:
        msg = 'Unsuccessfully posted to slack, response {}, {}'.format(resp.status, resp.code)
        LOGGER.error(msg)


def find_slack_user(username):
    """Helper func to return a mention if user matches

    If not will return the username so we at least has some identification

    Params:
    username (str): Username to find slack id

    Returns
    str: Slack id with the @ call out added IF found, just usenrame if not
    """

    norm_username = username.lower()
    if username in SLACK_USERS:
        return '<@{}>'.format(SLACK_USERS[username])
    else:
        return username


def prepare_message(users):
    """Prepares message for sending via webhook

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
                old_msgs.append('{}\'s key expires in {} days.'.format(u.slack_id, k.valid_for))

            if k.audit_state == 'expire':
                expired_msgs.append('{}\'s key is disabled.'.format(u.slack_id))



    old_attachment = {
        'title': 'IAM users with access keys expiring',
        'color': '#ffff00', #yellow
        'fields': [
            {
                'title': 'Users',
                'value': '\n'.join(old_msgs),
            }
        ]
    }

    expired_attachment = {
        'title': 'IAM users with disabled access keys',
        'color': '#ff0000', #red
        'fields': [
            {
                'title': 'Users',
                'value': '\n'.join(expired_msgs),
            }
        ]
    }

    howto_attachment = {
        'title': 'Access Key Rotation Instructions',
        'text': 'https://github.com/transcom/ppp-infra/tree/master/transcom-ppp#rotating-aws-access-keys'
    }


    # include master one
    msg = {
        # "text": "IAM Key Updates",
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
