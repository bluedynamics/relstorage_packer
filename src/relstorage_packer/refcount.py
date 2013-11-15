"""relstorage_packer - reference counter process"""
import datetime
import logging
import optparse
import sys
import time
from .utils import dbop
from .utils import get_references
from .utils import get_storage

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
    log.info("Create table object_refcount (drop existing).")
    stmt = """
    DROP TABLE IF EXISTS object_refcount;
    CREATE TABLE object_refcount (
        zoid       BIGINT NOT NULL UNIQUE,
        tid        BIGINT NOT NULL CHECK (tid > 0),
        refs       BIGINT[] NOT NULL DEFAULT ARRAY[]::integer[]
    );
    CREATE INDEX object_refcount_tid ON object_refcount (tid);
    CREATE INDEX object_refcount_refs ON object_refcount (refs);
    INSERT INTO object_refcount VALUES(1, 1);
    """
    cursor.execute(stmt)
    conn.commit()


def tid_boundary(conn, cursor):
    """get the latest handled tid from object_refcount or 0 if table is empty

    attention: the latest tid maybe processed incomplete after a prior run
    was stopped. so the latest tid need to get processed again with zoid/ tid
    combinations not present in object_refcount!
    """
    stmt = """
    SELECT DISTINCT tid FROM object_refcount ORDER BY tid DESC LIMIT 1;
    """
    cursor.execute(stmt)
    if not cursor.rowcount:
        return 0
    (tid,) = cursor.fetchone()
    log.debug("boundary transaction id to start with is: tid=%d" % tid)
    return tid


def next_tid(conn, cursor, lasttid):
    """generator iterating over distinct tids
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


def handle_transaction(conn, cursor, tid):
    log.debug('handle transaction %d' % tid)
    stmt = """
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
        _insert_empty_zoid(cursor, tid, source_zoid)
    conn.commit()


def _add_ref(cursor, tid, source_zoid, target_zoid):
    stmt = """
    UPDATE object_refcount
    SET tid=%(tid)d, refs=refs || %(source_zoid)d::bigint
    WHERE zoid=%(target_zoid)d
    AND %(source_zoid)d <> ALL(refs);

    INSERT INTO object_refcount (zoid, tid, refs)
       SELECT %(target_zoid)d, %(tid)d, ARRAY[%(source_zoid)d]
       WHERE NOT EXISTS (
           SELECT 1
           FROM object_refcount
           WHERE zoid=%(target_zoid)d
        );
    """ % {'source_zoid': source_zoid, 'target_zoid': target_zoid, 'tid': tid}
    cursor.execute(stmt)


def _check_removed_refs(cursor, tid, source_zoid, target_zoids):
    pass


def _insert_empty_zoid(cursor, tid, zoid):
    stmt = """
    INSERT INTO object_refcount (zoid, tid)
       SELECT %(zoid)d, %(tid)d
       WHERE NOT EXISTS (
           SELECT 1
           FROM object_refcount
           WHERE zoid=%(zoid)d
        );
    """ % {'zoid': zoid, 'tid': tid}
    cursor.execute(stmt)


def changed_tids_len(conn, cursor, tid):
    stmt = "SELECT COUNT(distinct tid) FROM object_state WHERE tid >=%d;" % tid
    cursor.execute(stmt)
    (count,) = cursor.next()
    return count or 0


def run(argv=sys.argv):
    log.info("Initiating packing.")

    parser = optparse.OptionParser(
        description='Fast ZODB Relstorage Packer for history free PostgreSQL',
        usage="%prog config_file"
    )
    parser.add_option(
        "--init", dest="initialize", default=False,
        action="store_true",
        help="Removes all reference counts and starts from scratch.",
    )
    options, args = parser.parse_args(argv[1:])
    if len(args) != 1:
        parser.error("The name of one configuration file is required.")
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
        overall_tids = dbop(storage, changed_tids_len, init_tid)
        processed_tids_offset = 0
        while True:
            tid = dbop(storage, next_tid, tid)
            if not tid:
                break
            dbop(storage, handle_transaction, tid)
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
                    '\nStats tids: '
                    '%s time | '
                    '%s eta (%s) | '
                    '%d '
                    '(%.3f%%) done | '
                    '%d todo | '
                    '%d all | '
                    '%d t/s | '
                    '%d t/delta' % (
                        str(duration),
                        str(eta),
                        str(time_left),
                        processed_tids,
                        tid_ratio,
                        tid_todo,
                        overall_tids,
                        tid_rate,
                        tid_rate_period,
                    )
                )
                logtime = time.time()
                processed_tids_offset = processed_tids
    except:
        log.error('Failed.')
        dbop(storage, release_counter_lock)
        storage.close()
        raise
    if processed_tids:
        processing_time = time.time() - start
        log.info(
            "Finished, processed in %s (%.2fs)" %
            (str(datetime.timedelta(seconds=processing_time)), processing_time)
        )
    else:
        log.info("Finished, there was nothing to do.")
    dbop(storage, release_counter_lock)
