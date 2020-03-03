from freezegun import freeze_time

import datetime
import pytest

from sleuth.services import format_slack_id


class TestFormatSlackID():
    def test_empty_input(self):
        """Test empty input"""
        resp = format_slack_id(None)
        assert resp == ''

        resp = format_slack_id('')
        assert resp == ''

    def test_unrecongized_input(self):
        """Test unrecognized input"""
        resp = format_slack_id('BLAH')
        assert resp == 'BLAH'

    def test_user_id(self):
        """Test a simple user id as input"""
        resp = format_slack_id('U12345')
        assert resp == '<@U12345>'

    def test_team_id(self):
        """Test a simple team id as input"""
        pass
