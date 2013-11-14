"""relstorage_packer - master process"""
import logging
import sys
import time
from .utils import dbop
from .utils import get_storage
from .utils import QUEUE_TABLE_NAME
from .utils import TARGET_TABLE_NAME

WAIT_DELAY = 1

log = logging.getLogger("master")


def aquire_master_lock(cursor):
    """try to acquire a master lock, if not possible log error and exit with 1
    """
    log.info("Acquiring master lock")
    cursor.execute("SELECT pg_try_advisory_lock(42)")
    locked = cursor.fetchone()[0]
    if not locked:
        log.error("Impossible to get Master Lock. Exit.")
        exit(0)


def release_master_lock(cursor):
    """release master lock
    """
    log.info("Releasing master lock")
    cursor.execute("SELECT pg_advisory_unlock(42)")


def queue_root(cursor):
    """queue ZODB root node, which has always zoid=0
    """
    log.info("Queuing ZODB root node")
    stmt = "INSERT INTO %s values(0);" % QUEUE_TABLE_NAME
    cursor.execute(stmt)


def cleanup_queue(cursor):
    log.debug('cleanup queue')
    stmt = """
    UPDATE %s SET taken=FALSE
    WHERE taken=TRUE AND finished=FALSE
    AND timestamp < now() - interval '3 seconds';
    COMMIT;
    """ % QUEUE_TABLE_NAME
    cursor.execute(stmt)


def get_queue_count_todo(cursor):
    stmt = "SELECT COUNT(*) FROM %s WHERE finished=FALSE;" % QUEUE_TABLE_NAME
    cursor.execute(stmt)
    (count,) = cursor.next()
    return count or 0


def get_queue_count_finished(cursor):
    stmt = "SELECT COUNT(*) FROM %s WHERE finished=TRUE;" % QUEUE_TABLE_NAME
    cursor.execute(stmt)
    (count,) = cursor.next()
    return count or 0


def get_queue_count_taken(cursor):
    stmt = "SELECT COUNT(*) FROM %s WHERE taken=TRUE AND finished=FALSE;" % \
           QUEUE_TABLE_NAME
    cursor.execute(stmt)
    (count,) = cursor.next()
    return count or 0


def get_queue_len(cursor):
    stmt = "SELECT COUNT(*) FROM %s;" % QUEUE_TABLE_NAME
    cursor.execute(stmt)
    (count,) = cursor.next()
    return count or 0


def finalize_pack(cursor):
    log.info("Finalizing packing")
    stmt = "SELECT COUNT(*) FROM %s;" % TARGET_TABLE_NAME
    cursor.execute(stmt)
    (target_count,) = cursor.next()
    stmt = "SELECT COUNT(*) FROM object_state;"
    cursor.execute(stmt)
    (source_count,) = cursor.next()
    log.info("Reduced from %d to %d by %d objects." %
             (source_count, target_count, source_count - target_count))
    log.debug("Moving over tables")
    start = time.time()
    stmt = """
    BEGIN;
    LOCK TABLE %(ttable)s, object_state  IN ACCESS EXCLUSIVE MODE;

    DROP INDEX object_state_tid;
    DROP TABLE object_state CASCADE;

    DROP CONSTRAINT blob_chunk_fk;
    DROP INDEX %(ttable)s_blob_chunk_lookup;
    DROP INDEX %(ttable)s_blob_chunk_loid;
    DROP TABLE %(ttable)s_blob_chunk;

    ALTER TABLE %(ttable)s RENAME TO object_state;
    ALTER INDEX %(ttable)s_tid RENAME TO object_state_tid;

    ALTER TABLE %(ttable)s_blob_chunk RENAME TO blob_chunk;
    ALTER INDEX %(ttable)s_blob_chunk_lookup RENAME TO blob_chunk_lookup;
    ALTER INDEX %(ttable)s_blob_chunk_loid RENAME TO blob_chunk_loid;
    ALTER CONSTRAINT %(ttable)s_blob_chunk_fk RENAME TO blob_chunk_fk;

    COMMIT;
    """ % {'ttable': TARGET_TABLE_NAME}
    log.debug(stmt)
    try:
        cursor.execute(stmt)
    except:
        cursor.execute('ABORT;')
    log.debug("Moving tables took: %.1fs" % (time.time() - start))


def run(argv=sys.argv):
    log.info("Initiating packing.")
    storage = get_storage(argv, __doc__, True)
    dbop(storage, aquire_master_lock)
    if storage.master_initialize:
        try:
            dbop(storage, queue_root)
        except:
            dbop(storage, release_master_lock)
            storage.close()
            raise
    # TODO: Remember transaction id persistent!
    processing_run = 0
    start = time.time()
    try:
        queue_count = dbop(storage, get_queue_count_todo)
        processing_run = bool(queue_count)
        leap_start = time.time()
        before_finished = dbop(storage, get_queue_count_finished)
        while queue_count:
            time.sleep(WAIT_DELAY)
            dbop(storage, cleanup_queue)  # cleanup hung entries
            finished = dbop(storage, get_queue_count_finished)
            queue_count = dbop(storage, get_queue_count_todo)
            leap_delta = time.time() - leap_start
            log.info("queue: % 8d open | % 3d work | % 8d done | % 8d all | % 3.2f obj/s" %
                     (queue_count,
                      dbop(storage, get_queue_count_taken),
                      dbop(storage, get_queue_count_finished),
                      dbop(storage, get_queue_len),
                      ((finished - before_finished) / leap_delta),
                      ))
            leap_start = time.time()
            before_finished = finished

    except:
        dbop(storage, release_master_lock)
        storage.close()
        raise
    if processing_run:
        queue_len = dbop(storage, get_queue_len)
        queue_time = time.time() - start
        log.info("Queue emptied in %ds with rate %3.2f obj/s" %
                 (queue_time, (float(queue_len) / queue_time)))
        start_finalizing = time.time()
        try:
            # dbop(storage, finalize_pack)
            log.info("Finalized in %d" % (time.time() - start_finalizing))
        except:
            log.warning('Finalizing failed')
            dbop(storage, release_master_lock)
            storage.close()
            raise
        log.info("Packing finished")
    else:
        log.info("Nothing happened so far.")
    dbop(storage, release_master_lock)
