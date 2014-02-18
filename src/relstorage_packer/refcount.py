"""relstorage_packer - reference numinrefs process"""
import datetime
import logging
import optparse
import os
import shutil
import sys
import time
from .utils import get_storage
from .utils import get_references
from .utils import get_conn_and_cursor
from .utils import dbcommit
from ZODB.utils import p64

WAIT_DELAY = 1
CYCLES_TO_RECONNECT = 20000

log = logging.getLogger("refcount")
log.setLevel(logging.INFO)

################################################################################
# Locking

@dbcommit
def aquire_lock(cursor):
    """
    try to acquire a numinrefs lock, if not possible log error and exit with 1
    """
    log.info("Acquiring numinrefs lock")
    cursor.execute("SELECT pg_try_advisory_lock(23)")
    locked = cursor.fetchone()[0]
    if not locked:
        log.error("Impossible to get numinrefs Lock. Exit.")
        exit(1)

@dbcommit
def release_lock(cursor):
    """release numinrefs lock
    """
    log.info("Releasing numinrefs lock")
    cursor.execute("SELECT pg_advisory_unlock(23)")


################################################################################
# Initialization

@dbcommit
def init_table(cursor):
    log.info("Create table object_inrefs (drop existing).")
    stmt = """
    DROP TABLE IF EXISTS object_inrefs;
    CREATE TABLE object_inrefs (
        zoid       BIGINT NOT NULL,
        tid        BIGINT NOT NULL CHECK (tid > 0),
        inref      BIGINT,
        numinrefs    BIGINT NOT NULL DEFAULT 0,
        PRIMARY KEY(zoid, inref)
    );
    CREATE INDEX object_inrefs_tid  ON object_inrefs (tid);
    CREATE INDEX object_inrefs_refs ON object_inrefs (inref);
    CREATE INDEX object_inrefs_numinrefs ON object_inrefs (numinrefs);
    """
    cursor.execute(stmt)

    stmt = """
    CREATE OR REPLACE
        FUNCTION add_inref(
            vfrom BIGINT, vto BIGINT, vtid BIGINT
        )
    RETURNS void
    AS $$
    DECLARE
        existing_ref boolean;
    BEGIN
        SELECT true
            INTO existing_ref
                FROM object_inrefs
                WHERE zoid = vto AND inref = vfrom;
        IF existing_ref THEN
            UPDATE object_inrefs
                SET tid = vtid
                WHERE zoid = vto AND inref = vto;
        ELSE
            INSERT INTO object_inrefs VALUES(vto, vtid, vfrom, 0);
            UPDATE object_inrefs
                SET numinrefs = numinrefs + 1
                WHERE zoid = vto AND inref = vto;
        END IF;
        RETURN;
    END;
    $$ LANGUAGE plpgsql;
    """
    cursor.execute(stmt)
    _add_ref(cursor, 0, 0, 1)
    _add_ref(cursor, -1, 0, 1)


################################################################################
# Fetching of Transaction Ids to be processed

def tid_boundary(cursor):
    """get the latest handled tid from object_inrefs or 0 if table is empty
    """
    stmt = """
    SELECT DISTINCT tid FROM object_inrefs ORDER BY tid DESC LIMIT 1;
    """
    cursor.execute(stmt)
    if not cursor.rowcount:
        return 0
    (tid,) = cursor.fetchone()
    log.debug("boundary transaction id to start with is: tid=%d" % tid)
    return tid


def next_tid(cursor, lasttid):
    """get next higher tid after given lasttid
    """
    stmt = """
    SELECT DISTINCT tid
    FROM object_state
    WHERE tid > %d
    ORDER BY tid ASC
    LIMIT 1
    """ % lasttid
    cursor.execute(stmt)
    if not cursor.rowcount:
        return None
    (tid,) = cursor.fetchone()
    log.debug("next transaction id to process is: tid=%d" % tid)
    return tid

def changed_tids_len(cursor, tid):
    stmt = "SELECT COUNT(distinct tid) FROM object_state WHERE tid >=%d;" % tid
    cursor.execute(stmt)
    (count,) = cursor.next()
    return count or 0


################################################################################
# Creation/ update of inverse references table and counters

def _add_ref(cursor, source_zoid, target_zoid, tid):
    """insert an entry to the refcount table or update tid on existing

    - on source_zoid there is reference to target_zoid
    - so we have source_zoid as incoming reference on target_zoid
    """
    stmt = """
    SELECT add_inref(%(source_zoid)d, %(target_zoid)d, %(tid)d);
    """ % {'source_zoid': source_zoid, 'target_zoid': target_zoid, 'tid': tid}
    cursor.execute(stmt)


def _check_removed_refs(cursor, source_zoid, target_zoids):
    """get all prior filed references of current source_zoid
       and remove any not valid anymore, in other words if there is an entry in
       ``object_inrefs`` with inref=source_zoid but its zoid is not in
       target_zoids, remove it and decrement the counter for zoid.
    """
    stmt = """
    SELECT zoid
    FROM object_inrefs
    WHERE inref = %(source_zoid)s
    AND zoid <> %(source_zoid)s;
    """ % {'source_zoid': source_zoid}
    cursor.execute(stmt)
    stmt = ""
    for zoid in cursor:
        zoid = zoid[0]
        if zoid in target_zoids:
            continue
        log.debug('    -> remove zoid=%d, inref=%d from object_inrefs' % (zoid, source_zoid))
        stmt += """
        DELETE FROM object_inrefs
        WHERE zoid = %(zoid)s
        AND inref = %(source_zoid)s;

        UPDATE object_inrefs
        SET numinrefs = numinrefs - 1
        WHERE zoid = %(zoid)s
        AND inref = %(zoid)s;
        """ % {'source_zoid': source_zoid,
               'zoid': zoid}
    if stmt:
        cursor.execute(stmt)

@dbcommit
def handle_transaction(cursor, tid, initialize):
    """analyze a given transaction and fill inverse references
    """
    log.debug('handle transaction %d' % tid)
#    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    stmt = """
    BEGIN;
    SELECT zoid, state
    FROM object_state
    WHERE tid = %d
    ORDER BY zoid;
    """ % tid
    cursor.execute(stmt)
    # cursor is needed, so store in array
    result = [(zoid, get_references(state)) for zoid, state in cursor]
    for source_zoid, target_zoids in result:
        log.debug('-> processing zoid=%d' % (source_zoid))
        log.debug('   found %d refs' % len(target_zoids))
        _add_ref(cursor, source_zoid, source_zoid, tid)
        for target_zoid in target_zoids:
            log.debug('   -> process reference to %s' % target_zoid)
            _add_ref(cursor, target_zoid, target_zoid, tid)
            _add_ref(cursor, source_zoid, target_zoid, tid)

        if not initialize:
            _check_removed_refs(cursor, source_zoid, target_zoids)

    # commit whole handled tid, so we are sure to have it complete in numinrefs
    # funny part: this is multiple times faster than commit per source_zoid!


################################################################################
# Removal of orphaned objects

def _get_orphaned_zoid(cursor):
    stmt = """
    SELECT zoid
    FROM object_inrefs
    WHERE numinrefs = 1
    LIMIT 1;
    """
    cursor.execute(stmt)
    if not cursor.rowcount:
        return None
    (zoid,) = cursor.fetchone()
    log.debug("selected orphaned object: zoid=%d" % zoid)
    return zoid


def _remove_blob(storage, zoid):
    if storage.blobhelper is None:
        log.debug('-> No blobstorage available')
        return
    fshelper = storage.blobhelper.fshelper
    blobpath = fshelper.getPathForOID(p64(zoid))
    log.debug('-> Blobs for zoid=%s are at %s' % (zoid, blobpath))
    if not os.path.exists(blobpath):
        log.debug('-> No Blobs to remove')
        return
    log.debug('-> Remove Blobs')
    shutil.rmtree(blobpath)
    # here traversal up and removal of empty directories makes sense.
    # otherwise there are many empty directories left.
    # need to check side effects first!


def _remove_zoid(cursor, zoid):
    """
    remove a zoid completly.
    - remove all references in object_inrefs (this includes self reference)
    - remove entry in object_state
    """
    # handle references (remove, decrement)
    stmt = """
    SELECT zoid, state
    FROM object_state
    WHERE zoid = %d;
    """ % zoid
    cursor.execute(stmt)

    source_zoid, state = cursor.fetchone()
    target_zoids = get_references(state)
    stmt = ""
    for target_zoid in target_zoids:
        stmt += """
        DELETE FROM object_inrefs
        WHERE zoid = %(target_zoid)s
        AND inref = %(source_zoid)s;

        UPDATE object_inrefs
        SET numinrefs = numinrefs - 1
        WHERE zoid = %(target_zoid)s
        AND inref = %(target_zoid)s;
        """ % {'source_zoid': source_zoid,
               'target_zoid': target_zoid}

    # finally delete data
    stmt += """
    DELETE FROM object_inrefs
    WHERE zoid =  %(zoid)s;

    DELETE FROM object_state
    WHERE zoid =  %(zoid)s;
    """ % {'zoid': zoid}
    cursor.execute(stmt)


def remove_orphans(connection, cursor, storage):
    """remove orphans with blobs

    do transactions in here manually, because of blobs
    """
    tick = time.time()
    count = 0
    while True:
        zoid = _get_orphaned_zoid(cursor)
        if zoid is None:
            break
        log.debug('-> Remove orphaned with zoid=%s' % zoid)
        try:
            _remove_zoid(cursor, zoid)
            cursor.close()
            connection.commit()
        except:
            connection.rollback()
            raise
        _remove_blob(storage, zoid)
        count += 1

        if (count % CYCLES_TO_RECONNECT) == 0:
            # get a fresh connection, else postgres server may consume too
            # much RAM .oO( sigh )
            log.info('Refresh connection after {0} zoid cycles'.format(count))
            connection.close()
            connection, cursor = get_conn_and_cursor(storage)
        else:
            # only refresh closed cursor
            cursor = connection.cursor()


        cursor = connection.cursor()
        if (time.time() - tick) > 5:
            log.info('Removed %s orphaned objects' % count)
            tick = time.time()
    log.info('finished removal of %s orphaned objects' % count)


################################################################################
# Main Runner

def run(argv=sys.argv):
    parser = optparse.OptionParser(
        description='Fast ZODB Relstorage Packer for history free PostgreSQL',
        usage="%prog config_file"
    )
    parser.add_option(
        "-i", "--init", dest="initialize", default=False,
        action="store_true",
        help="Removes all reference counts and starts from scratch.",
    )
    parser.add_option(
        "-v", "--verbose", dest="verbose", default=False,
        action="store_true",
        help="More verbose output, includes debug messages.",
    )
    options, args = parser.parse_args(argv[1:])
    if len(args) != 1:
        parser.error("The name of one configuration file is required.")
    if options.verbose:
        log.setLevel(logging.DEBUG)
        log.debug("Logging in verbose mode.")

    log.info("Initiating packing.")

    storage = get_storage(args[0])
    connection, cursor = get_conn_and_cursor(storage)
    aquire_lock(connection, cursor)
    cursor = connection.cursor()

    if options.initialize:
        try:
            init_table(connection, cursor)
            cursor = connection.cursor()
        except:
            release_lock(connection, cursor)
            storage.close()
            raise
    processed_tids = 0
    start = logtime = time.time()
    try:
        init_tid = tid = tid_boundary(cursor)
        log.info('Fetching number of all transactions from database...')
        overall_tids = changed_tids_len(cursor, init_tid)
        log.info('Found %d transactions in database.' % overall_tids)
        processed_tids_offset = 0
        initialize = options.initialize

        # BUILD/ UPDATE INVERSE REFERENCES
        while True:
            tid = next_tid(cursor, tid)
            if not tid:
                break

            # BUILD/UPDATE FOR TID
            handle_transaction(connection, cursor, tid, initialize=initialize)
            processed_tids += 1
            if (processed_tids % CYCLES_TO_RECONNECT) == 0:
                # get a fresh connection, else postgres server may consume too
                # much RAM .oO( sigh )
                connection.close()
                log.info(
                    'Refresh connection after {0} tid cycles'.format(
                        processed_tids
                    )
                )
                connection, cursor = get_conn_and_cursor(storage)
            else:
                # only refresh closed cursor
                cursor = connection.cursor()

            # Statistics
            if time.time() - logtime > 1:
                # calc/print some stats
                period = time.time() - logtime
                duration = datetime.timedelta(seconds=time.time() - start)
                tid_delta_period = processed_tids - processed_tids_offset
                tid_rate_period = tid_delta_period / period
                tid_ratio = processed_tids / float(overall_tids) * 100
                tid_todo = overall_tids - processed_tids
                tid_rate = processed_tids / (time.time() - start)
                time_left = ((time.time() - start) / processed_tids) * tid_todo
                time_left = datetime.timedelta(seconds=time_left)
                eta = datetime.datetime.now() + time_left
                log.info(
                    'Processed %.3f%% | '
                    '%s elapsed | '
                    '%s eta (in %s) | '
                    '%d done | '
                    '%d of %d left | '
                    '%.1f t/s | '
                    '%.1f t/delta' % (
                        tid_ratio,
                        str(duration).rsplit('.', 1)[0],
                        eta.strftime('%Y-%m-%d %H:%M'),
                        str(time_left).rsplit('.', 1)[0],
                        processed_tids,
                        tid_todo,
                        overall_tids,
                        tid_rate,
                        tid_rate_period,
                    )
                )
                logtime = time.time()
                processed_tids_offset = processed_tids
        processing_time = time.time() - start
        log.info(
            'Finished analyzation phase after %s (%.2fs)' %
            (str(datetime.timedelta(seconds=processing_time)), processing_time)
        )
        cleanup_start = time.time()

        # REMOVE
        remove_orphans(connection, cursor, storage)

        processing_time = time.time() - cleanup_start
        log.info(
            'Finished cleanup phase after %s (%.2fs)' %
            (str(datetime.timedelta(seconds=processing_time)), processing_time)
        )
    except Exception, e:
        log.error(e.message)
        raise
        exit(1)
    finally:
        cursor = connection.cursor()
        release_lock(connection, cursor)
        connection.close()
        storage.close()

    if processed_tids:
        processing_time = time.time() - start
        log.info(
            "Completed: processed %s transaction in %s-mode in %s (%.2fs) " %
            (processed_tids,
             'init' if options.initialize else 'update',
             str(datetime.timedelta(seconds=processing_time)),
             processing_time)
        )
    else:
        log.info("Completed, there was nothing to do.")
