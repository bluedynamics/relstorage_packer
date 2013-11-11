import logging
import optparse
from StringIO import StringIO
import ZConfig
from ZODB.serialize import referencesf
from ZODB.utils import u64

schema_xml = """
<schema>
  <import package="ZODB"/>
  <import package="relstorage"/>
  <multisection type="ZODB.storage" attribute="storages" />
</schema>
"""

QUEUE_TABLE_NAME = 'relstorage_packer_queue'
TARGET_TABLE_NAME = 'relstorage_packer_target'


def dbop(storage, func, *args, **kwargs):
    """wrapper to private method in order to call a given function with
    connection, cursor and optionally given args and kwargs.
    """
    def func_wo_conn(conn, cursor, *args, **kwargs):
        return func(cursor, *args, **kwargs)

    return storage._with_store(func_wo_conn, *args, **kwargs)


def _create_queue_table(cursor, drop):
    cursor.execute('BEGIN;')
    if drop:
        logging.info('Dropping existing queue table.')
        cursor.execute("DROP TABLE IF EXISTS %s;" % QUEUE_TABLE_NAME)
    else:
        stmt = "SELECT * FROM pg_tables WHERE tablename='%s';" % \
               QUEUE_TABLE_NAME
        cursor.execute(stmt)
        if bool(cursor.rowcount):
            logging.info('Keeping existing queue table.')
            return
    logging.info('Creating queue table.')
    stmt = """
    CREATE TABLE %s (
        zoid        BIGINT NOT NULL,
        taken       BOOLEAN NOT NULL DEFAULT FALSE,
        timestamp   TIMESTAMP,
        counter     bigserial primary key
    );
    """ % QUEUE_TABLE_NAME
    cursor.execute(stmt)
    cursor.execute('COMMIT;')


def _create_target_table(cursor, drop):
    cursor.execute('BEGIN;')
    if drop:
        logging.info('Dropping existing target table.')
        cursor.execute("DROP TABLE IF EXISTS %s;" % TARGET_TABLE_NAME)
    else:
        stmt = "SELECT * FROM pg_tables WHERE tablename='%s';" % \
               TARGET_TABLE_NAME
        cursor.execute(stmt)
        if bool(cursor.rowcount):
            logging.info('Keeping existing target table.')
            return
    logging.info('Creating target table.')
    stmt = """
    CREATE TABLE %s (
        zoid        BIGINT NOT NULL PRIMARY KEY,
        tid         BIGINT NOT NULL CHECK (tid > 0),
        state_size  BIGINT NOT NULL CHECK (state_size >= 0),
        state       BYTEA
    );
    CREATE INDEX %s_tid ON %s (tid);
    """ % (TARGET_TABLE_NAME, TARGET_TABLE_NAME, TARGET_TABLE_NAME)
    cursor.execute(stmt)
    cursor.execute('COMMIT;')


def get_storage(argv, description, is_master=False):
    master_initialize = False
    parser = optparse.OptionParser(
        description=description,
        usage="%prog config_file"
    )
    if is_master:
        parser.add_option(
            "--init", dest="initialize", default=False,
            action="store_true",
            help="Puts root object in queue.",
        )
    options, args = parser.parse_args(argv[1:])
    if is_master:
        master_initialize = options.initialize

    if len(args) != 1:
        parser.error("The name of one configuration file is required.")

    config_file = args[0]

    schema = ZConfig.loadSchemaFile(StringIO(schema_xml))
    config, dummy = ZConfig.loadConfig(schema, config_file)
    if len(config.storages) < 1:
        raise ValueError('No storages configured')
    connection = config.storages[0]
    if connection.config.keep_history:
        raise RuntimeError('Packing does not support history keeping storages')
    name = '%s (%s)' % ((connection.name or 'storage'),
                        connection.__class__.__name__)
    logging.info("Opening %s...", name)
    storage = connection.open()
    logging.info("Successfully openend %s", storage.getName())
    if 'PostgreSQLAdapter' not in storage.getName():
        raise RuntimeError('Only PostgreSQL databases are supported')
    if is_master:
        setattr(storage, 'master_initialize', master_initialize)
    dbop(storage, _create_queue_table, master_initialize)
    dbop(storage, _create_target_table, master_initialize)
    return storage

def get_references(state):
    """Return the set of OIDs the given state refers to."""
    refs = set()
    if state:
        for oid in referencesf(str(state)):
            refs.add(u64(oid))
    return refs


