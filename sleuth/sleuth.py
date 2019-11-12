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

class Key():
    username = ""
    key_id = ""
    created = None
    status = ""
    audit_state = None

    age = 0
    valid_for = 0

    def __init__(self, username, key_id, status, created):
        self.username = username
        self.key_id = key_id
        self.status = status
        self.created = created

        self.age = (dt.datetime.now(dt.timezone.utc) - self.created).days

    def audit(self, rotate_age, expire_age):
        """
        Audits the key and sets the status state based on key age

        Note if the key is below rotate the audit_state=good. If the key is disabled will be marked as disabled.

        Parameters:
        rotate (int): Age key must be before audit_state=old
        expire (int): Age key must be before audit_state=expire

        Returns:
        None
        """
        assert(rotate_age < expire_age)

        self.valid_for = expire_age - self.age

        if self.age < rotate_age:
            self.audit_state = 'good'
        if self.age >= rotate_age and self.age < expire_age:
            self.audit_state = 'old'
        if self.age >= expire_age:
            self.audit_state = 'expire'
        if self.status == 'Inactive':
            self.audit_state = 'disabled'



class User():
    username = ""
    user_id = ""
    slack_id = ""
    keys = []

    def __init__(self, user_id, username, slack_id=None):
        self.user_id = user_id
        self.username = username
        self.slack_id = slack_id

    def audit(self, rotate=80, expire=90):
        for k in self.keys:
            k.audit(rotate, expire)



def get_iam_key_info(user):
    """Fetches User key info

    Parameters:
    user (str): user to fetch key info for

    Returns:
    list (Key): Return list of keys for a single user
    """
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
    pag = IAM.get_paginator('list_users')
    iter = pag.paginate()

    users = []
    for resp in iter:
        for u in resp['Users']:
            user = User(u['UserId'], u['UserName'], find_user(u['UserName']))
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


def print_key_report(users):
    """Prints table of report

    Parameters:
    users(list): Users with key related information

    Returns:
    None
    """

    tbl_data = []

    for u in users:
        for k in u.keys:
            tbl_data.append([
                u.username,
                u.slack_id,
                k.key_id,
                k.audit_state,
                k.valid_for
            ])

    print(tabulate(tbl_data, headers=['UserName', 'Slack ID', 'Key ID', 'Status', 'Expires in Days']))


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


def audit():
    LOGGER.info('Sleuth running')
    iam_users = get_iam_users()

    # lets audit keys so the ages and state are set
    for u in iam_users:
        u.audit(80, 90)

    #mainly for debugging
    print_key_report(iam_users)

    # lets disabled expired keys and build list of old and expired for slack
    for u in iam_users:
        for k in u.keys:
            if k.audit_state == 'expire':
                disable_key(k, u.username)


    # lets send slack messages
    send_to_slack, slack_msg = prepare_message(iam_users)
    if send_to_slack:
        send_slack_message(slack_msg)
    else:
        LOGGER.info('Nothing to report')


if __name__ == '__main__':
    audit()
