import logging
import optparse
from StringIO import StringIO
import ZConfig
from ZODB.serialize import referencesf
from ZODB.utils import u64

log = logging.getLogger("utils")

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

    def func_conn(conn, cursor, *args, **kwargs):
        return func(conn, cursor, *args, **kwargs)

    return storage._with_store(func_conn, *args, **kwargs)


def _create_queue_table(cursor, drop):
    cursor.execute('BEGIN;')
    if drop:
        log.info('Dropping existing queue table.')
        cursor.execute("DROP TABLE IF EXISTS %s;" % QUEUE_TABLE_NAME)
        log.debug('DROPPED')
    else:
        stmt = "SELECT * FROM pg_tables WHERE tablename='%s';" % \
               QUEUE_TABLE_NAME
        cursor.execute(stmt)
        if bool(cursor.rowcount):
            log.info('Keeping existing queue table.')
            return
    log.info('Creating queue table.')
    stmt = """
    CREATE TABLE %(qtable)s (
        zoid        BIGINT NOT NULL UNIQUE,
        taken       BOOLEAN NOT NULL DEFAULT FALSE,
        timestamp   TIMESTAMP,
        finished    BOOLEAN NOT NULL DEFAULT FALSE,
        counter     bigserial primary key
    );
    CREATE INDEX %(qtable)s_zoid ON %(qtable)s (zoid);
    CREATE INDEX %(qtable)s_taken_false ON %(qtable)s (taken)
        WHERE taken = false;
    CREATE INDEX %(qtable)s_taken_true ON %(qtable)s (taken)
        WHERE taken = true;
    CREATE INDEX %(qtable)s_finished_false ON %(qtable)s (finished)
        WHERE finished = false;
    CREATE INDEX %(qtable)s_finished_true ON %(qtable)s (finished)
        WHERE finished = true;

    CREATE FUNCTION COPYZOID(zoid bigint) RETURNS setof void as $$
    DECLARE
    BEGIN
        RETURN;
    END;
    $$ LANGUAGE plpgsql;

    COMMIT;


    """ % {'qtable': QUEUE_TABLE_NAME, 'ttable': TARGET_TABLE_NAME}
    cursor.execute(stmt)


def _create_target_table(cursor, drop):
    cursor.execute('BEGIN;')
    if drop:
        log.info('Dropping existing target table.')
        stmt = """
        DROP TABLE IF EXISTS %(ttable)s_blob_chunk CASCADE;
        DROP TABLE IF EXISTS %(ttable)s CASCADE;
        COMMIT;
        """ % {'ttable': TARGET_TABLE_NAME}
        cursor.execute(stmt)
    else:
        stmt = "SELECT * FROM pg_tables WHERE tablename='%s';" % \
               TARGET_TABLE_NAME
        cursor.execute(stmt)
        if bool(cursor.rowcount):
            log.info('Keeping existing target table.')
            return
    log.info('Creating target table.')
    stmt = """
    CREATE TABLE %(ttable)s (
        zoid        BIGINT NOT NULL PRIMARY KEY,
        tid         BIGINT NOT NULL CHECK (tid > 0),
        state_size  BIGINT NOT NULL CHECK (state_size >= 0),
        state       BYTEA
    );
    CREATE INDEX %(ttable)s_tid ON %(ttable)s (tid);



    CREATE TABLE %(ttable)s_blob_chunk (
        zoid        BIGINT NOT NULL,
        chunk_num   BIGINT NOT NULL,
                    PRIMARY KEY (zoid, chunk_num),
        tid         BIGINT NOT NULL,
        chunk       OID NOT NULL
    );
    CREATE INDEX %(ttable)s_blob_chunk_lookup ON %(ttable)s_blob_chunk (zoid);
    CREATE INDEX %(ttable)s_blob_chunk_loid ON %(ttable)s_blob_chunk (chunk);
    ALTER TABLE %(ttable)s_blob_chunk ADD CONSTRAINT %(ttable)s_blob_chunk_fk
        FOREIGN KEY (zoid)
        REFERENCES %(ttable)s (zoid)
        ON DELETE CASCADE;

    COMMIT;
    """ % {'ttable': TARGET_TABLE_NAME}
    log.debug(stmt)
    cursor.execute(stmt)


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
    log.info("Opening %s...", name)
    storage = connection.open()
    log.info("Successfully openend %s", storage.getName())
    if 'PostgreSQLAdapter' not in storage.getName():
        raise RuntimeError('Only PostgreSQL databases are supported')
    if is_master:
        setattr(storage, 'master_initialize', master_initialize)
    # dbop(storage, _create_queue_table, master_initialize)
    # dbop(storage, _create_target_table, master_initialize)
    return storage

def get_references(state):
    """Return the set of OIDs the given state refers to."""
    refs = set()
    if state:
        for oid in referencesf(str(state)):
            refs.add(u64(oid))
    return refs

    

