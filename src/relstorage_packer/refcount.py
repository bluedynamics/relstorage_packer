"""relstorage_packer - reference counter process"""
import datetime
import logging
import optparse
import os
import shutil
import sys
import time
from .utils import dbop
from .utils import get_references
from .utils import get_storage
from ZODB.utils import p64

WAIT_DELAY = 1

log = logging.getLogger("refcount")
log.setLevel(logging.INFO)


def aquire_counter_lock(conn, cursor):
    """try to acquire a counter lock, if not possible log error and exit with 1
    """
    log.info("Acquiring counter lock")
    cursor.execute("SELECT pg_try_advisory_lock(23)")
    locked = cursor.fetchone()[0]
    if not locked:
        log.error("Impossible to get Counter Lock. Exit.")
        exit(0)


def release_counter_lock(conn, cursor):
    """release counter lock
    """
    log.info("Releasing counter lock")
    cursor.execute("SELECT pg_advisory_unlock(23)")


def init_table(conn, cursor):
    log.info("Create table object_inrefs (drop existing).")
    stmt = """
    DROP TABLE IF EXISTS object_inrefs;
    CREATE TABLE object_inrefs (
        zoid       BIGINT NOT NULL,
        tid        BIGINT NOT NULL CHECK (tid > 0),
        inref      BIGINT,
        PRIMARY KEY(zoid, inref)
    );
    CREATE INDEX object_inrefs_tid  ON object_inrefs (tid);
    CREATE INDEX object_inrefs_refs ON object_inrefs (inref);

    INSERT INTO object_inrefs VALUES(0, 1, 0);
    INSERT INTO object_inrefs VALUES(0, 1, -1);
    """
    cursor.execute(stmt)
    conn.commit()


def tid_boundary(conn, cursor):
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


def next_tid(conn, cursor, lasttid):
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


def _add_ref(cursor, tid, source_zoid, target_zoid):
    """insert an entry to the refcount table or update tid on existing
    """
    stmt = """
    INSERT
        INTO object_inrefs (zoid, tid, inref)
        SELECT %(target_zoid)d, %(tid)d, %(source_zoid)d
        WHERE NOT EXISTS (
            SELECT 1
            FROM object_inrefs
            WHERE
                zoid = %(target_zoid)d
                AND inref = %(source_zoid)d
        )
    ;
    UPDATE object_inrefs
        SET tid=%(tid)d
        WHERE
            zoid=%(target_zoid)d
            AND inref = %(source_zoid)d
    ;
    """ % {'source_zoid': source_zoid, 'target_zoid': target_zoid, 'tid': tid}
    cursor.execute(stmt)


def _insert_empty_zoid(cursor, tid, zoid):
    """Insert zoid if not already there in a pg-cheap way.
    its a self-reference, so objects without any incoming refs are represented
    with one entry, the self-reference where zoid=inref.
    """
    stmt = """
    INSERT
       INTO object_inrefs (zoid, tid, inref)
       SELECT %(zoid)d, %(tid)d, %(zoid)d
       WHERE NOT EXISTS (
           SELECT 1
           FROM object_inrefs
           WHERE zoid=%(zoid)d
           AND inref=%(zoid)d
        );
    """ % {'zoid': zoid, 'tid': tid}
    cursor.execute(stmt)


def _check_removed_refs(cursor, source_zoid, target_zoids):
    """remove all rows in object_inrefs where source_zoid is in refs and
    object_inrefs.zoid is not in target_zoids
    """
    if target_zoids:
        stmt = """
        DELETE FROM object_inrefs
        WHERE inref = %(source_zoid)s
        AND zoid NOT IN (%(target_zoids)s);
        """ % {'source_zoid': source_zoid,
               'target_zoids': ', '.join([str(_) for _ in target_zoids])}
    else:
        stmt = """
        DELETE FROM object_inrefs
        WHERE inref = %(source_zoid)s
        """ % {'source_zoid': source_zoid}
    cursor.execute(stmt)


def handle_transaction(conn, cursor, tid, initialize):
    """analyze a given transaction and fill inverse references
    """
    log.debug('handle transaction %d' % tid)
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
        for target_zoid in target_zoids:
            log.debug('   -> process reference to %s' % target_zoid)
            # import ipdb; ipdb.set_trace()
            _add_ref(cursor, tid, source_zoid, target_zoid)
        if not initialize:
            _check_removed_refs(cursor, source_zoid, target_zoids)
        _insert_empty_zoid(cursor, tid, source_zoid)

    # commit whole handled tid, so we are sure to have it complete in counters
    # funny part: this is twice as fast than commit per source_zoid!
    conn.commit()


def _get_orphaned_zoid(conn, cursor):
    stmt = """
    SELECT zoid
    FROM object_inrefs
    GROUP BY zoid
    HAVING count(inref) = 1
    ORDER BY zoid;
    """
    cursor.execute(stmt)
    if not cursor.rowcount:
        return None
    (zoid,) = cursor.fetchone()
    log.debug("selected orphaned object: zoid=%d" % zoid)
    return zoid


def _remove_blob(storage, zoid):
    fshelper = storage.blobhelper.fshelper
    blobpath = fshelper.getPathForOID(p64(zoid))
    log.debug('Blobs for zoid=%s are at %s' % (zoid, blobpath))
    if not os.path.exists(blobpath):
        log.debug('-> Nothing to remove')
        return
    log.debug('-> Remove blobs')
    shutil.rmtree(blobpath)


def _remove_zoid(conn, cursor, zoid):
    """
    remove a zoid completly.
    - remove all references in object_inrefs (this includes self reference)
    - remove entry in object_state
    """
    stmt = """
    DELETE FROM object_inrefs
    WHERE inref = %(zoid)s;

    DELETE FROM object_state
    WHERE zoid =  %(zoid)s;
    """ % {'zoid': zoid}
    cursor.execute(stmt)
    conn.commit()


def remove_orphans(storage):
    while True:
        zoid = dbop(storage, _get_orphaned_zoid)
        if zoid is None:
            break
        log.debug('Remove orphaned with zoid=%s' % zoid)
        _remove_blob(storage, zoid)
        dbop(storage, _remove_zoid, zoid)


def changed_tids_len(conn, cursor, tid):
    stmt = "SELECT COUNT(distinct tid) FROM object_state WHERE tid >=%d;" % tid
    cursor.execute(stmt)
    (count,) = cursor.next()
    return count or 0


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
    dbop(storage, aquire_counter_lock)

    if options.initialize:
        try:
            dbop(storage, init_table)
        except:
            dbop(storage, release_counter_lock)
            storage.close()
            raise
    processed_tids = 0
    start = logtime = time.time()
    try:
        init_tid = tid = dbop(storage, tid_boundary)
        log.info('Fetching number of all transactions from database...')
        overall_tids = dbop(storage, changed_tids_len, init_tid)
        log.info('Found %d transactions in database.' % overall_tids)
        processed_tids_offset = 0
        initialize = options.initialize
        while True:
            tid = dbop(storage, next_tid, tid)
            if not tid:
                break
            dbop(
                storage,
                handle_transaction,
                tid,
                initialize=initialize
            )
            processed_tids += 1
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
        remove_orphans(storage)
        processing_time = time.time() - cleanup_start
        log.info(
            'Finished cleanup phase after %s (%.2fs)' %
            (str(datetime.timedelta(seconds=processing_time)), processing_time)
        )
    except Exception, e:
        log.error(e.message)
        dbop(storage, release_counter_lock)
        storage.close()
        exit(1)
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
    dbop(storage, release_counter_lock)
