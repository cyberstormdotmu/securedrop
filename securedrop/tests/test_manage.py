# -*- coding: utf-8 -*-

import argparse
import io
import datetime
import logging
import os
import manage
import mock
import sys
import time

from StringIO import StringIO

os.environ['SECUREDROP_ENV'] = 'test'  # noqa

from models import Journalist, db
from utils import db_helper


YUBIKEY_HOTP = ['cb a0 5f ad 41 a2 ff 4e eb 53 56 3a 1b f7 23 2e ce fc dc',
                'cb a0 5f ad 41 a2 ff 4e eb 53 56 3a 1b f7 23 2e ce fc dc d7']


def test_parse_args(config):
    # just test that the arg parser is stable
    manage.get_args(config)


def test_not_verbose(caplog, config):
    args = manage.get_args(config).parse_args(['run'])
    manage.setup_verbosity(args)
    manage.log.debug('INVISIBLE')
    assert 'INVISIBLE' not in caplog.text


def test_verbose(caplog, config):
    args = manage.get_args(config).parse_args(['--verbose', 'run'])
    manage.setup_verbosity(args)
    manage.log.debug('VISIBLE')
    assert 'VISIBLE' in caplog.text


def test_get_username_success():
    with mock.patch("__builtin__.raw_input", return_value='jen'):
        assert manage._get_username() == 'jen'


def test_get_username_fail():
    bad_username = 'a' * (Journalist.MIN_USERNAME_LEN - 1)
    with mock.patch("__builtin__.raw_input",
                    side_effect=[bad_username, 'jen']):
        assert manage._get_username() == 'jen'


def test_get_yubikey_usage_yes():
    with mock.patch("__builtin__.raw_input", return_value='y'):
        assert manage._get_yubikey_usage()


def test_get_yubikey_usage_no():
    with mock.patch("__builtin__.raw_input", return_value='n'):
        assert not manage._get_yubikey_usage()


# Note: we use the `journalist_app` fixture because it creates the DB
def test_handle_invalid_secret(journalist_app, config, mocker):
    """Regression test for bad secret logic in manage.py"""

    mocker.patch("manage._get_username", return_value='ntoll'),
    mocker.patch("manage._get_yubikey_usage", return_value=True),
    mocker.patch("__builtin__.raw_input", side_effect=YUBIKEY_HOTP),
    mocker.patch("sys.stdout", new_callable=StringIO),

    # We will try to provide one invalid and one valid secret
    return_value = manage._add_user(config)

    assert return_value == 0
    assert 'Try again.' in sys.stdout.getvalue()
    assert 'successfully added' in sys.stdout.getvalue()


# Note: we use the `journalist_app` fixture because it creates the DB
def test_exception_handling_when_duplicate_username(journalist_app,
                                                    config,
                                                    mocker):
    """Regression test for duplicate username logic in manage.py"""

    mocker.patch("manage._get_username", return_value='foo-bar-baz')
    mocker.patch("manage._get_yubikey_usage", return_value=False)
    mocker.patch("sys.stdout", new_callable=StringIO)

    # Inserting the user for the first time should succeed
    return_value = manage._add_user(config)
    assert return_value == 0
    assert 'successfully added' in sys.stdout.getvalue()

    # Inserting the user for a second time should fail
    return_value = manage._add_user(config)
    assert return_value == 1
    assert ('ERROR: That username is already taken!' in
            sys.stdout.getvalue())


# Note: we use the `journalist_app` fixture because it creates the DB
def test_delete_user(journalist_app, config, mocker):
    mocker.patch("manage._get_username", return_value='test-user-56789')
    mocker.patch("manage._get_yubikey_usage", return_value=False)
    mocker.patch("manage._get_username_to_delete",
                 return_value='test-user-56789')
    mocker.patch('manage._get_delete_confirmation', return_value=True)

    return_value = manage._add_user(config)
    assert return_value == 0

    return_value = manage.delete_user(None, config)
    assert return_value == 0


# Note: we use the `journalist_app` fixture because it creates the DB
def test_delete_non_existent_user(journalist_app, config, mocker):
    mocker.patch("manage._get_username_to_delete",
                 return_value='does-not-exist')
    mocker.patch('manage._get_delete_confirmation', return_value=True)
    mocker.patch("sys.stdout", new_callable=StringIO)

    return_value = manage.delete_user(None, config)
    assert return_value == 0
    assert 'ERROR: That user was not found!' in sys.stdout.getvalue()


def test_get_username_to_delete(mocker):
    mocker.patch("__builtin__.raw_input", return_value='test-user-12345')
    return_value = manage._get_username_to_delete()
    assert return_value == 'test-user-12345'


def test_reset(journalist_app, test_journo, alembic_config, config):
    # Override the hardcoded alembic.ini value
    config.TEST_ALEMBIC_INI = alembic_config

    args = argparse.Namespace(store_dir=config.STORE_DIR)
    return_value = manage.reset(args, config)

    assert return_value == 0
    assert os.path.exists(config.DATABASE_FILE)
    assert os.path.exists(config.STORE_DIR)

    # Verify journalist user present in the database is gone
    with journalist_app.app_context():
        res = Journalist.query \
            .filter_by(username=test_journo['username']).one_or_none()
        assert res is None


def test_get_username(mocker):
    mocker.patch("__builtin__.raw_input", return_value='foo-bar-baz')
    assert manage._get_username() == 'foo-bar-baz'


def test_clean_tmp_do_nothing(caplog, config):
    args = argparse.Namespace(days=0,
                              directory=' UNLIKELY::::::::::::::::: ',
                              verbose=logging.DEBUG)
    manage.setup_verbosity(args)
    manage.clean_tmp(args, config)
    assert 'does not exist, do nothing' in caplog.text


def test_clean_tmp_too_young(config, caplog):
    args = argparse.Namespace(days=24*60*60,
                              directory=config.TEMP_DIR,
                              verbose=logging.DEBUG)
    # create a file
    io.open(os.path.join(config.TEMP_DIR, 'FILE'), 'a').close()

    manage.setup_verbosity(args)
    manage.clean_tmp(args, config)
    assert 'modified less than' in caplog.text


def test_clean_tmp_removed(config, caplog):
    args = argparse.Namespace(days=0,
                              directory=config.TEMP_DIR,
                              verbose=logging.DEBUG)
    fname = os.path.join(config.TEMP_DIR, 'FILE')
    with io.open(fname, 'a'):
        old = time.time() - 24*60*60
        os.utime(fname, (old, old))
    manage.setup_verbosity(args)
    manage.clean_tmp(args, config)
    assert 'FILE removed' in caplog.text


def test_were_there_submissions_today(source_app, config):
    data_root = config.SECUREDROP_DATA_ROOT
    args = argparse.Namespace(data_root=data_root,
                              verbose=logging.DEBUG)

    with source_app.app_context():
        count_file = os.path.join(data_root, 'submissions_today.txt')
        source, codename = db_helper.init_source_without_keypair()
        source.last_updated = (datetime.datetime.utcnow() -
                               datetime.timedelta(hours=24*2))
        db.session.commit()
        manage.were_there_submissions_today(args, config)
        assert io.open(count_file).read() == "0"
        source.last_updated = datetime.datetime.utcnow()
        db.session.commit()
        manage.were_there_submissions_today(args, config)
        assert io.open(count_file).read() == "1"
