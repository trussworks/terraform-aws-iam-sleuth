from freezegun import freeze_time

import datetime
import pytest

from sleuth.services import format_slack_id, prepare_sns_message, prepare_slack_message
from sleuth.auditor import Key, User

created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
lastused = created = datetime.datetime(2019, 1, 3, tzinfo=datetime.timezone.utc)
# 4 users to represent the 4 audit states
user1 = User('user1', 'slackuser1', 'U12345')
key1 = Key('user1', 'asdfksakfa', 'Active', created, lastused)
key1.audit_state = 'old'

user2 = User('user2', 'slackuser2', 'U67890')
key2 = Key('user2', 'ldasfkk', 'Active', created, lastused)
key2.audit_state = 'expire'

user3 = User('user3', 'slackuser3', 'U13579')
key3 = Key('user3', 'oithsetc', 'Active', created, lastused)
key3.audit_state = 'stagnant'

user4 = User('user4', 'slackuser4', 'U24680')
key4 = Key('user4', 'bajaoietnb', 'Active', created, lastused)
key4.audit_state = 'stagnant_expire'

user1.keys = [key1]
user2.keys = [key2]
user3.keys = [key3]
user4.keys = [key4]
users = [user1, user2, user3, user4]

class TestFormatSlackID():
    def test_empty_input(self):
        """Test empty input"""
        # None input
        resp = format_slack_id(None)
        assert resp == 'UNKNOWN'

        # empty input
        resp = format_slack_id('')
        assert resp == 'UNKNOWN'

    def test_unrecognized_input(self):
        """Test unrecognized input"""
        resp = format_slack_id('BLAH')
        assert resp == 'BLAH'

    def test_user_id(self):
        """Test a simple user id as input"""
        resp = format_slack_id('U12345')
        assert resp == '<@U12345>'

    def test_team_id(self):
        """Test a simple team id as input, no display name"""
        resp = format_slack_id('subteam-T12345')
        assert resp == '(see log) <!subteam^T12345>'

    def test_team_id_missing_hyphen(self):
        """Test a team id missing a '-' as input"""
        resp = format_slack_id('subteamT12345')
        assert resp == 'subteamT12345'

    def test_team_id_passing_displayname(self):
        """Test a team id with display name"""
        resp = format_slack_id('subteam-T12345', 'Joe123')
        assert resp == 'Joe123 (<!subteam^T12345>)'

    def test_sns_message_customization(self, monkeypatch):
        """Test that the sns message can be customized"""
        title = 'This is the SNS message'
        addltext = 'boop boop'

        t2 = 'INACTIVE WARNING'
        tadd = 'Inactive instructions'

        send_to_sns, msg = prepare_sns_message(users, title, addltext, t2, tadd)
        assert title in msg
        assert addltext in msg
        assert t2 in msg
        assert tadd in msg

    def test_slack_message_customization(self, monkeypatch):
        """Test that the slack message can be customized"""
        title = 'SLACK TITLE'
        addltext = 'Slack content'

        t2 = 'INACTIVE WARNING'
        tadd = 'Inactive instructions'

        send_to_slack, msg = prepare_slack_message(users, title, addltext, t2, tadd)

        assert len(msg['attachments']) == 6
        last_attachment = msg['attachments'][0]
        assert last_attachment['title'] == title
        assert last_attachment['text'] == addltext

        # Test for the different message contexts
        old="IAM users with access keys expiring due to creation age"
        exp="IAM users with disabled access keys due to creation age"
        stgn="IAM users with access keys expiring due to inactivity. \n Please login to AWS to prevent key from being disabled"
        stgn_exp="IAM users with disabled access keys due to inactivity"
        assert msg['attachments'][1]['title'] == old
        assert msg['attachments'][2]['title'] == exp
        assert msg['attachments'][3]['title'] == stgn_exp
        assert msg['attachments'][4]['title'] == t2
        assert msg['attachments'][4]['text'] == tadd
        assert msg['attachments'][5]['title'] == stgn

