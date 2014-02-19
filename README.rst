relstorage_packer
=================

Packs a ZODB in a *history-free* PostgreSQL RelStorage with blobs in
filesystem.


Overview
--------

This script works also for very large Relstorage ZODBs with several million
objects. The original pack script took several days and consumed lots of RAM.
So there was need to accelerate the process of packing.

This script does not consume relevant amounts of RAM, runs much faster than the
original. Where the old took 3.5 days only for analysis it takes now about 6
hours. On subsequent runs it only processes changes after last run: it
considers only transactions newer than last processed transaction of the prior
run.

At time of writing processing 44mio objects takes initially about 3-6h
depending on hardware and configuration of Postgresql.

The script creates an inverse object graph, this takes little extra space in DB.


Limitations
-----------

At time of development the critical production environment was a postgresql
database running relstorage with blobs stored on a fileserver in history free
mode. So this is implemented.

I'am sure its easily possible to make this work on MySQL and Oracle too.
Also considering blobs inside DB is for sure possible.

I'am not sure if this way of cleanup makes sense for non-history-free mode. At
least it needs a lot of love and understanding of ZODB to refactor and
implement.

Contributions are welcome!


Usage
-----

Create a configuration file. It is the same as used in classical pack script
deployed with Relstorage::

    <relstorage>
        create-schema false
        keep-history false
        shared-blob-dir true
        blob-dir var/blobstorage
        commit-lock-timeout 600
        <postgresql>
            dsn dbname='test_site' host='127.0.0.1' user='zodb' password='secret'
        </postgresql>
    </relstorage>

After installation a script ``relstorage_pack`` is available::

    Usage: relstorage_pack config_file

    Fast ZODB Relstorage Packer for history free PostgreSQL
    
    Options:
      -h, --help     show this help message and exit
      -i, --init     Removes all reference counts and starts from scratch.
      -v, --verbose  More verbose output, includes debug messages.

When running first time with your database pass ``--init`` as parameter. This
drops and recreates the packing table.


How it works
============

At first run it creates a table ``object_inrefs`` used for inverse reference
counting. The table has:

``zoid BIGINT NOT NULL,``
    this is the object id where incoming references are counted  for

``tid BIGINT NOT NULL CHECK (tid > 0)``
    transaction id of the zoid

``inref BIGINT,``
    the object id of the incoming reference OR
    the same as zoid.

``numinrefs BIGINT NOT NULL DEFAULT 0,``
    if zoid==inref this is the counter field, otherwise it is not relevant.

So this table is used for two different things:

1) keeping track of the incoming references

2) counting the incoming references.

The code runs in three main phases:

initial preparation phase
    creates missing tables, cleans object_inrefs table and runs through all
    transactions in order to count and record all transactions.

subsequent runs preparation phase
    1) starts at last know tid and then runs through all new
       transactions in order to count and record changes of new transactions.
    2) for each new transaction zoid (current) check also if there where
       references gone meanwhile. so get all prior filed references of current
       and remove any not valid anymore. For each removed decrement the counter
       on ``object_inrefs`` where zoid=reference and inref=reference.

cleanup phase
    1) select an orphan, a zoid with no incoming refs
    2) get all zoids referenced by this orphan
    3) for each of this reference delete the entry from ``object_inrefs`` where
       inref=orphan and zoid=reference
    4) decrement counter on the entry where zoid=reference and inref=reference
    5) delete the entry with the orphaned zoid from ``object_state`` (real data)
    6) start with (1) unless theres no orphan any more.


Source Code
===========

The sources are in a GIT DVCS with its main branches at
`github <http://github.com/bluedynamics/relstorage_packer>`_.

We'd be happy to see many forks and pull-requests to make this package even
better.

Using integrated buildout and testing
-------------------------------------

Testing this code i not easy and writing good tests is a task to be done.
At the moment you can try the code bu running a
postgres database on localhost (unless you want to change ``buildout.cfg``).
Then run as database-user (named ``postgres`` on debian) the commands::

    psql -c "CREATE USER zope WITH PASSWORD 'secret';"
    psql -c "CREATE DATABASE relstorage_packer_test OWNER zope;"
    psql -c "REVOKE connect ON DATABASE relstorage_packer_test FROM PUBLIC;"
    psql -c "GRANT connect ON DATABASE relstorage_packer_test TO zope;"
 
Next (because of my laziness) run ``./bin/instance start`` which starts a Plone.
Add a Plone Site, add and delete some content to fill the database with
something to pack.

Next run the packer.

If you dont like this: pull requests are always welcome.

Contributors
============

- Jens W. Klein <jens@bluedynamics.com> (Maintainer)

Thanks to Robert Penz for some good ideas at our Linux User Group Tirol Meeting.
Also thanks to Shane Hathaway for ``Relstorage`` and Jim Fulton for ZODB and
``zc.zodbdgc`` (which unfortunately does not work with Relstorage).
