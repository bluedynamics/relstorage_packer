relstorage_packer
=================

Packs a ZODB in a history free PostgreSQL RelStorage with blobs in filesystem.

Overview
--------

This works also for very large Relstorage ZODBs with several million objects. 
The original pack script took several days and consumed lots of RAM.

This script does not consume relevant amounts of RAM, runs much faster (where 
the old took 3,5 days it takes now 6 hours). On subsequent runs it only
processes changes after last run: it considers only transactions newer than 
last processed transaction of the prior run.

At time of writing processing 44mio objects takes initially about 3-6h 
depending on hardware and configuration of Postgresql. 

The script creates an inverse object graph, this takes some extra space in DB.

Limitations
-----------

At time of development the critical production environment was a postgresql 
database running relstorage with blobs stored on a fileserver in history free
mode. 

I'am sure its easily possible to make this work on MySQL and Oracle too. 
Also considering blobs in DB is for sure possible. 

I'am not sure if this way of cleanup makes sense for non-history-free mode. At 
least it needs a lot of love and understanding of ZODB to refactor and 
implement.

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
      -h, --help  show this help message and exit
      --init      Removes all reference counts and starts from scratch.

When running first time with your database pass ``--init`` as parameter. This
drops and recreates the packing table.

  
 
Source Code
===========

The sources are in a GIT DVCS with its main branches at 
`github <http://github.com/bluedynamics/relstorage_packer>`_.

We'd be happy to see many forks and pull-requests to make this package even 
better.

Contributors
============

- Jens W. Klein <jens@bluedynamics.com> (Maintainer)

Thanks to Robert Penz for some good ideas at our Linux User Group Tirol Meeting.