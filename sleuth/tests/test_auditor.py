from freezegun import freeze_time

import datetime
import pytest

from sleuth.auditor import Key

@freeze_time("2019-01-16")
class TestKey():
    def test_normal(self):
        """Normal happy path, key is good"""
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        k = Key('username', 'keyid', 'Active', created, last_used)
        k.audit(60, 80, 20, 19)
        assert k.creation_age == 15
        assert k.audit_state == 'good'

    def test_rotate_expiration(self):
        """Key is past rotate age, key is marked as old"""
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('username', 'keyid', 'Active', created, last_used)
        key.audit(10, 80, 20, 19)
        assert key.audit_state == 'old'

    def test_rotate_access(self):
        """Key is past last accessed age, key is marked as old"""
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('username', 'keyid', 'Active', created, last_used)
        key.audit(60, 80, 20, 10)
        assert key.audit_state == 'stagnant'

    def test_old_expiration(self):
        """Key is past max expiration threshold, key is marked as expired"""
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('username', 'keyid', 'Active', created, last_used)
        key.audit(10, 11, 10, 8)
        assert key.audit_state == 'expire'

    def test_old_access(self):
        """Key is past max access age threshold, key is marked as expired"""
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('username', 'keyid', 'Active', created, last_used)
        key.audit(60, 80, 10, 9)
        assert key.audit_state == 'stagnant_expire'

    def test_no_disable(self, monkeypatch):
        """Key is disabled AWS status of Inactive, but disabling is turned off so key remains audit state expire"""
        monkeypatch.setenv('ENABLE_AUTO_EXPIRE', 'false')
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('user2', 'ldasfkk', 'Inactive', created, last_used)
        key.audit(10, 11, 10, 8)
        assert key.audit_state == 'expire'

    def test_last_used(self, monkeypatch):
        """Key has not been used in X days, key marked is disabled"""
        monkeypatch.setenv('ENABLE_AUTO_EXPIRE', 'true')
        monkeypatch.setenv('INACTIVITY_AGE', '10')
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('user3', 'kljin', 'Active', created, last_used)
        key.audit(10, 11, 2, 1)
        assert key.audit_state == 'expire'
        key.audit(60, 80, 2, 1)
        assert key.audit_state == 'stagnant_expire'

    def test_disabled(self, monkeypatch):
        """Key is disabled AWS status of Inactive, key marked is disabled"""
        monkeypatch.setenv('ENABLE_AUTO_EXPIRE', 'true')
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('user2', 'ldasfkk', 'Inactive', created, last_used)
        key.audit(10, 11, 10, 8)
        assert key.audit_state == 'disabled'
        key.audit(60, 80, 30, 20)
        assert key.audit_state == 'disabled'

    def test_invalid(self):
        """Key is disabled AWS status of Inactive, key marked is disabled"""
        created = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
        last_used = datetime.datetime(2019, 1, 2, tzinfo=datetime.timezone.utc)
        key = Key('user2', 'ldasfkk', 'Inactive', created, last_used)
        with pytest.raises(AssertionError):
            key.audit(5, 1, 1, 1)
