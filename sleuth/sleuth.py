import datetime as dt
import logging


import boto3
from pythonjsonlogger import jsonlogger
from tabulate import tabulate

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
            print(u)
            u['keys'] = get_iam_key_info(u['UserName'])
            users.append(u)

    return users


# inspect users to find old IAM keys

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

    print(tabulate(tbl_data))

# pull slack users

# match IAM user to slack user

# push notification to integration with list of upcoming

# if user is past threshold disable key


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


if __name__ == '__main__':
    audit()
