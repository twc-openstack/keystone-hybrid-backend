# Copyright 2012-2014 SUSE Linux Products GmbH
# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""Hybrid Identity backend for Keystone on top of the LDAP and SQL backends"""

from keystone.common import dependency
from keystone.common import sql
from keystone.common import utils
from keystone import exception
from keystone.identity.backends import base
from keystone.identity.backends import ldap as ldap_backend
from keystone.identity.backends import sql as sql_ident

from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF
LOG = log.getLogger(__name__)


@dependency.requires('assignment_api')
class Identity(sql_ident.Identity):
    def __init__(self, *args, **kwargs):
        super(Identity, self).__init__(*args, **kwargs)
        self.user = ldap_backend.UserApi(CONF)
        self.domain_aware = True

    # Identity interface
    def authenticate(self, user_id, password):
        """Authenticate based on a user and password.

        Tries to authenticate using the SQL backend first, if that fails
        it tries the LDAP backend.

        """
        if not password:
            raise AssertionError('Invalid user / password')
        with sql.session_for_read() as session:
            try:
                user_ref = self._get_user(session, user_id)
            except exception.UserNotFound:
                raise AssertionError('Invalid user / password')

            # if the user_ref has a password, it's from the SQL backend and
            # we can just check if it coincides with the one we got
            conn = None
            try:
                assert utils.check_password(password, user_ref.password)
            except TypeError:
                raise AssertionError('Invalid user / password')
            except (KeyError, AssertionError):  # if it doesn't have a password, it must be LDAP
                try:
                    user_name = user_ref['name']
                    # get_connection does a bind for us which checks the password
                    conn = self.user.get_connection(self.user._id_to_dn(user_name),
                                                    password, end_user_auth=True)
                    assert conn
                except Exception:
                    raise AssertionError('Invalid user / password')
                else:
                    LOG.debug("Authenticated user with LDAP.")
                    self.domain_aware = False
                finally:
                    if conn:
                        conn.unbind_s()
            else:
                LOG.debug("Authenticated user with SQL.")
            return base.filter_user(user_ref.to_dict())

    def is_domain_aware(self):
        # XXX we only need domain_aware to be False when authenticating
        # as an LDAP user; after that, all operations will be done on
        # the SQL database and domain_aware needs to be True. This code
        # makes the assumption that the result of authenticate() should
        # be read as not domain_aware (for LDAP), after which
        # domain_aware should revert to True.
        domain_aware = self.domain_aware
        if not self.domain_aware:
            self.domain_aware = True
        return domain_aware

    def _get_user(self, session, user_id):
        # try SQL first
        user_ref = super(Identity, self)._get_user(session, user_id)
        return user_ref
        # we don't want to do any lookups to LDAP since we rely
        # on local copies of SQL users.
#        try:
#            user_ref = super(Identity, self)._get_user(session, user_id)
#        except exception.UserNotFound:
#            # then try LDAP
#            return self.user.get(user_id)
#        else:
#            return user_ref

    def get_user(self, user_id):
        LOG.debug("Called get_user %s" % user_id)
        with sql.session_for_read() as session:
            user = self._get_user(session, user_id)
            try:
                user = user.to_dict()
            except AttributeError:
                # LDAP Users are already dicts which is fine
                pass
            return base.filter_user(user)

    def get_user_by_name(self, user_name, domain_id):
        LOG.debug("Called get_user_by_name %s, %s" % (user_name, domain_id))
        # try SQL first
        try:
            user = super(Identity, self).get_user_by_name(user_name, domain_id)
        except exception.UserNotFound:
            # then try LDAP
            return base.filter_user(self.user.get_by_name(user_name))
        else:
            return user

    def list_users(self, hints):
        sql_users = super(Identity, self).list_users(hints)
        return sql_users
#        ldap_users = self.user.get_all_filtered()
#        return sql_users + ldap_users
