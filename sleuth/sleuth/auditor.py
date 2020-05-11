import datetime as dt
import json
import logging
import os


from pythonjsonlogger import jsonlogger
from tabulate import tabulate

from sleuth.services import get_iam_users, disable_key, send_slack_message, send_sns_message, prepare_slack_message, prepare_sns_message

LOGGER = logging.getLogger('sleuth')

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

        # set the valid_for in the object
        self.valid_for = expire_age - self.age

        # lets audit the age
        if self.age < rotate_age:
            self.audit_state = 'good'
        if self.age >= rotate_age and self.age < expire_age:
            self.audit_state = 'old'
        if self.age >= expire_age:
            self.audit_state = 'expire'
        if self.status == 'Inactive' and os.environ['ENABLE_AUTO_EXPIRE'] == 'true':
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
                k.age
            ])

    print(tabulate(tbl_data, headers=['UserName', 'Slack ID', 'Key ID', 'Status', 'Age in Days']))


def audit():
    LOGGER.info('Sleuth running')
    iam_users = get_iam_users()


    # lets audit keys so the ages and state are set
    for u in iam_users:
        u.audit(os.environ['WARNING_AGE'], os.environ['EXPIRATION_AGE'])

    #mainly for debugging
    print_key_report(iam_users)
    print(os.environ['ENABLE_AUTO_EXPIRE'])
    # lets disabled expired keys and build list of old and expired for slack
    if os.environ['ENABLE_AUTO_EXPIRE'] == 'true':
        for u in iam_users:
            for k in u.keys:
                if k.audit_state == 'expire':
                    disable_key(k, u.username)

    if 'SNS_TOPIC' not in os.environ and 'SLACK_URL' not in os.environ:
        LOGGER.warn('No notification settings set, please set SNS_TOPIC or SLACK_URL envar!')

    # lets assemble and send slack msg
    if 'SNS_TOPIC' in os.environ:
        LOGGER.info('Detected SNS setting so preparing and sending message via SNS')
        send_to_slack, slack_msg = prepare_sns_message(iam_users)

        if send_to_slack:
            send_sns_message(os.environ['SNS_TOPIC'], slack_msg)
        else:
            LOGGER.info('Nothing to report')


    if 'SLACK_URL' in os.environ:
        LOGGER.info('Using direct Slack API')
        # lets assemble the slack message
        send_to_slack, slack_msg = prepare_slack_message(iam_users)

        if send_to_slack:
            send_slack_message(os.environ['SLACK_URL'], slack_msg)
        else:
            LOGGER.info('Nothing to report')
