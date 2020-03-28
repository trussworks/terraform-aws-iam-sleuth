from freezegun import freeze_time

import datetime
import pytest

from sleuth.services import format_slack_id


class TestFormatSlackID():
    def test_empty_input(self):
        """Test empty input"""
        # None input
        resp = format_slack_id(None)
        assert resp == 'UNKNOWN'

        # empty input
        resp = format_slack_id('')
        assert resp == 'UNKNOWN'

    def test_unrecongized_input(self):
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
