from freezegun import freeze_time

import datetime
import pytest

from sleuth.services import format_slack_id, prepare_sns_message, prepare_slack_message
from sleuth.auditor import Key, User

created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
user1 = User('user1', 'slackuser1', 'U12345')
user2 = User('user1', 'slackuser1', 'U67890')
key1 = Key('user1', 'asdfksakfa', 'Active', created)
key1.audit_state = 'old'
key2 = Key('user2', 'ldasfkk', 'Active', created)
key2.audit_state = 'expire'
user1.keys = [key1]
user2.keys = [key2]
users = [user1, user2]

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

        send_to_sns, msg = prepare_sns_message(users, title, addltext)
        assert title in msg
        assert addltext in msg

    def test_slack_message_customization(self, monkeypatch):
        """Test that the slack message can be customized"""
        title = 'SLACK TITLE'
        addltext = 'Slack content'

        send_to_slack, msg = prepare_slack_message(users, title, addltext)

        assert len(msg['attachments']) == 3
        last_attachment = msg['attachments'][0]
        assert last_attachment['title'] == title
        assert last_attachment['text'] == addltext
