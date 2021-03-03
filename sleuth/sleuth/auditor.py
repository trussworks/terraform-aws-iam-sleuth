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
    inactivity = None
    audit_state = None

    creation_age = 0
    access_age = 0
    valid_for = 0

    def __init__(self, username, key_id, status, created, inactivity_age):
        self.username = username
        self.key_id = key_id
        self.status = status
        self.created = created
        self.inactivity_age = inactivity_age

        self.creation_age = (dt.datetime.now(dt.timezone.utc) - self.created).days
        self.access_age = (dt.datetime.now(dt.timezone.utc) - self.inactivity_age).days

    def audit(self, rotate_age, expire_age, max_inactivity_age, inactivity_warning_age):
        """
        Audits the key and sets the status state based on key creation age and last used age

        Note if the key is below rotate or last used age, the audit_state=good.
        If the key is disabled will be marked as disabled.

        Parameters:
        rotate (int): Age key must be before audit_state=old
        expire (int): Age key must be before audit_state=expire
        inactivity_age (int): Age of last key usage must be before audit_state=expire
        inactivity_warning_age (int): Age of last key usage must be before audit_state=old

        Returns:
        None
        """
        assert(rotate_age < expire_age)
        assert(max_inactivity_age <= expire_age)
        assert(inactivity_warning_age < max_inactivity_age)

        # set the valid_for in the object
        self.valid_for = expire_age - self.creation_age

        # lets audit the age
        if self.creation_age >= expire_age:
            self.audit_state = 'expire'
        elif self.access_age >= max_inactivity_age:
            self.audit_state = 'expire'
        # audit key age and last used age
        elif (self.creation_age >= rotate_age and self.creation_age < expire_age) or (self.access_age >= inactivity_warning_age and self.access_age < max_inactivity_age):
            self.audit_state = 'old'
        elif self.creation_age < rotate_age:
            self.audit_state = 'good'

        # lets audit the status
        if self.status == 'Inactive' and os.environ.get('ENABLE_AUTO_EXPIRE', False) == 'true':
            self.audit_state = 'disabled'

class User():
    username = ""
    user_id = ""
    slack_id = ""
    auto_expire = ""
    keys = []

    def __init__(self, user_id, username, slack_id=None, auto_expire=None):
        self.user_id = user_id
        self.username = username
        self.slack_id = slack_id
        self.auto_expire = auto_expire

    def audit(self, rotate=80, expire=90, inactivity=90, inactivity_warn=80):
        for k in self.keys:
            k.audit(rotate, expire, inactivity, inactivity_warn)

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
                u.auto_expire,
                k.audit_state,
                k.creation_age,
                k.access_age
            ])

    print(tabulate(tbl_data, headers=['UserName', 'Slack ID', 'Key ID', 'AutoExpire', 'Status', 'Age in Days', 'Last Access Age']))


def audit():
    iam_users = get_iam_users()

    # Check for optional env vars
    if os.environ.get('INACTIVITY_AGE') and not os.environ.get('INACTIVITY_WARNING_AGE'):
        raise RuntimeError('Must set env var INACTIVITY_WARNING_AGE if INACTIVITY_AGE is set')

    # lets audit keys so the ages and state are set
    for u in iam_users:
        # Do not audit keys that are set to not allow auto-expire
        if u.auto_expire.lower()=='false':
            LOGGER.info('{} key is set to not expire'.format(u.username))
            for k in u.keys:
                k.audit_state='good'
        else:
            # Do not require last used age, set to expiration age as default
            u.audit(int(os.environ['WARNING_AGE']), int(os.environ['EXPIRATION_AGE']), int(os.environ.get('INACTIVITY_AGE', os.environ['EXPIRATION_AGE'])), int(os.environ.get('INACTIVITY_WARNING_AGE', os.environ['WARNING_AGE'])))

    if os.environ.get('DEBUG', False):
        print_key_report(iam_users)

    # lets disabled expired keys and build list of old and expired for slack
    if os.environ.get('ENABLE_AUTO_EXPIRE', False) == 'true':
        for u in iam_users:
            for k in u.keys:
                if k.audit_state == 'expire':
                    disable_key(k, u.username)
    else:
        LOGGER.warn('Cannot disable AWS Keys, ENABLE_AUTO_EXPIRE set to False')

    MSG_TITLE = os.environ.get('NOTIFICATION_TITLE', 'AWS IAM Key Report')
    MSG_TEXT = os.environ.get('NOTIFICATION_TEXT', '')

    # lets assemble the SNS message
    if os.environ.get('SNS_TOPIC', None) is not None:
        LOGGER.info('Detected SNS settings, preparing and sending message via SNS')
        send_to_slack, slack_msg = prepare_sns_message(iam_users, MSG_TITLE, MSG_TEXT)

        if send_to_slack:
            send_sns_message(os.environ['SNS_TOPIC'], slack_msg)
        else:
            LOGGER.info('Nothing to report')


    # lets assemble and send Slack msg
    if os.environ.get('SLACK_URL', None) is not None:
        LOGGER.info('Detected Slack settings, preparing and sending message via Slack API')
        # lets assemble the slack message
        send_to_slack, slack_msg = prepare_slack_message(iam_users, MSG_TITLE, MSG_TEXT)

        if send_to_slack:
            send_slack_message(os.environ['SLACK_URL'], slack_msg)
        else:
            LOGGER.info('Nothing to report')
