# hybrid SQL and LDAP backends for OpenStack Keystone

The code in this branch has only been tested on the **stable/kilo** branch
of OpenStack Keystone! Check out the other git branches if you need code for
different OpenStack releases.

This project provides two alternative backends for Keystone:

## The Identity Backend

This allows authentication with LDAP **and** SQL while using the SQL backend
for all the usual operations. No users or groups are copied from LDAP. LDAP
users are assigned a default role and tenant when they first login if they
don't already have one (user_project_metadata table). For granting roles to
users (`keystone user-role-add`), only the user id from LDAP is inserted into
the SQL backend.

* * *

### Installation

Since this backend relies on both the LDAP and SQL backends, you have to
configure both beforehand. Use the usual configuration options found in
/etc/keystone/keystone.conf. However, from the LDAP backend's config, only the
ldap.user options will be used by the hybrid backend (so no tenant/role
options).

You should try to see that user authentication works fine with the LDAP backend
*before* trying on the hybrid backend. Also make sure that `keystone user-list`
works using the LDAP identity backend.

Install this module using the `pip install` command against this directory or
repository.

Set the identity backend to `hybrid` (it will use both the LDAP and the SQL
backends under the hood):

```
[identity]
driver = keystone.identity.backends.hybrid_identity.Identity
```

Restart keystone.

Now you can assign custom roles to users in LDAP. Make sure you use one of the
LDAP user-ids returned by the `keystone user-list` query.

```
keystone user-role-add --user-id=12345 --role-id <role-id> --tenant-id <tenant-id>
```
