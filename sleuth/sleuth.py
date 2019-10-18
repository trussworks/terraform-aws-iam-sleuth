import datetime as dt
import json
import logging


import boto3
from pythonjsonlogger import jsonlogger
from tabulate import tabulate
import requests

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

logHandler = logging.StreamHandler()
supported_keys = [
            'asctime',
            'created',
            'filename',
            'funcName',
            'levelname',
            'levelno',
            'lineno',
            'module',
            'msecs',
            'message',
            'name',
            'process',
            'processName',
            'relativeCreated',
        ]

log_format = lambda x: ['%({0:s})'.format(i) for i in x]
custom_format = ' '.join(log_format(supported_keys))

formatter = jsonlogger.JsonFormatter(custom_format)
logHandler.setFormatter(formatter)
LOGGER.addHandler(logHandler)

IAM = boto3.client('iam')
SSM = boto3.client('ssm')

SLACK_USERS = {
    'lee': 'UP6A26UAE'
}

def get_iam_key_info(user):
    """Fetches User key info

    Parameters:
    user (str): user to fetch key info for

    Returns:
    dict:AWS response on key info
    """
    resp = IAM.list_access_keys(UserName=user)
    return resp['AccessKeyMetadata']

def get_iam_users():
    """Fetches IAM users WITH key info

    Parameters:
    None

    Resturs:
    list:IAM user info along with access key info
    """
    pag = IAM.get_paginator('list_users')
    iter = pag.paginate()

    users = []
    for resp in iter:
        for u in resp['Users']:
            u['keys'] = get_iam_key_info(u['UserName'])
            users.append(u)

    return users


def audit_key(key, rotate_age=80, expire_age=90):
    """Looks at key info and determines if out of compliance.

    Parameters:
    key (dicts): Key info of user to inspect in boto json format
    rotate_age (int): Days when a key is considered to be rotated, must be less than expire_age
    expire_age (int): Days when key will be expired, must be greater than rotate_age

    Returns:
    int: Age of key in days
    int: number of days till expire_age is met
    str: State of the key: disabled, good, old, expire
    """
    assert(rotate_age < expire_age)


    age = (dt.datetime.now(dt.timezone.utc) - key['CreateDate']).days
    valid_for = expire_age - age

    if key['Status'] == 'Inactive':
        return age, valid_for, 'disabled'

    if age < rotate_age:
        return age, valid_for, 'good'
    if age >= rotate_age and age < expire_age:
        return age, valid_for, 'old'
    if age >= expire_age:
        return age, valid_for, 'expire'


def disable_key(user, key):
    """Disables an AWS access key

    Parameters:
    user (str): User ID of key to disable
    key (str): Key ID to disable

    Returns:
    None
    """
    LOGGER.info('Disabling key {} for User {}'.format(key, user))
    IAM.update_access_key(UserName=user,
                          AccessKeyId=key,
                          Status='Inactive')
    LOGGER.info('Successfully disabled key {} for User {}'.format(key, user))


def print_key_report(users, status_filter=None):
    """Prints table of report

    Parameters:
    users(list): Users with key related information

    Returns:
    None
    """

    tbl_data = []

    for u in users:
        for k in u['keys']:
            tbl_data.append([
                u['UserName'],
                k['AccessKeyId'],
                k['Valid'],
                k['ExpiresIn']
            ])

    print(tabulate(tbl_data, headers=['UserName', 'Key ID', 'Status', 'Expires in Days']))


# push notification to integration with list of upcoming

# if user is past threshold disable key

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


def send_slack_message(payload):
    webhook = get_ssm_value('/integrations/test_general')

    resp = requests.post(webhook, data=json.dumps(payload),
                         headers={'Content-Type': 'application/json'})

    if resp.status_code == requests.codes.ok:
        LOGGER.info('Successfully posted to slack')
    else:
        msg = 'Unsuccessfully posted to slack, response {}, {}'.format(resp.status, resp.code)
        LOGGER.error(msg)


def find_user(username):
    """Helper func to return a mention if user matches
    """

    norm_username = username.lower()
    if username in SLACK_USERS:
        return '<@{}>'.format(SLACK_USERS[username])
    else:
        return username


def prepare_message(old_users, expired_users):
    """Prepares message for sending via webhook

    Parameters:
    old_users (list): Dicts containing user and key age
    expired_users (list): Dicts containing user and key age

    Returns:
    None
    """

    old_attachment = {
        'title': 'IAM users with access keys expiring',
        'color': '#ffff00', #yellow
        'fields': [
            {
                'title': 'Users',
                'value': '\n'.join(['{}\'s key expires in {} days'.format(find_user(u['UserName']), u['ExpiresIn'])for u in old_users]),
            }
        ]
    }

    expired_attachment = {
        'title': 'IAM users with disabled access keys',
        'color': '#ff0000', #red
        'fields': [
            {
                'title': 'Users',
                'value': '\n'.join(['{}\'s key is disabled'.format(find_user(u['UserName'])) for u in expired_users]),
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

    # only add the attachments that have users
    if len(old_users) > 0:
        msg['attachments'].append(old_attachment)

    if len(expired_users) > 0:
        msg['attachments'].append(expired_attachment)



    # only post to slack if needed
    if len(msg['attachments']) > 0:
        msg['attachments'].append(howto_attachment)
        send_slack_message(msg)
    else:
        LOGGER.info('Nothing to report')


def audit():
    LOGGER.info('Sleuth running')
    iam_users = get_iam_users()
    for u in iam_users:
        for k in u['keys']:
            age, valid_for, valid = audit_key(k)
            k['Age'] = age
            k['ExpiresIn'] = valid_for
            k['Valid'] = valid


    #mainly for debugging
    print_key_report(iam_users)

    old_keys_info = []
    expired_keys_info = []
    # lets take actions on keys
    for u in iam_users:
        for k in u['keys']:
            if k['Valid'] == 'old':
                LOGGER.info('User {} has an old key'.format(u['UserName']))
                old_keys_info.append({
                    'UserName': u['UserName'],
                    'AccessKeyId': k['AccessKeyId'],
                    'Valid': k['Valid'],
                    'ExpiresIn': k['ExpiresIn']
                })

            if k['Valid'] == 'expire':
                LOGGER.info('User {} key will be disabled'.format(u['UserName']))
                disable_key(u['UserName'], k['AccessKeyId'])
                expired_keys_info.append({
                    'UserName': u['UserName'],
                    'AccessKeyId': k['AccessKeyId'],
                    'Valid': k['Valid'],
                    'ExpiresIn': k['ExpiresIn']
                })

    slack_msg = prepare_message(old_keys_info, expired_keys_info)


if __name__ == '__main__':
    audit()
