import logging
import sys
import time
from .utils import dbop
from .utils import get_references
from .utils import get_storage
from .utils import QUEUE_TABLE_NAME
from .utils import TARGET_TABLE_NAME
import psycopg2

EMTPY_DELAY = 1

log = logging.getLogger("worker")
log.setLevel(logging.INFO)


def _get_and_lock_next_zoid(cursor):
    stmt = """
    LOCK TABLE %(qtable)s IN SHARE ROW EXCLUSIVE MODE;
    UPDATE %(qtable)s
    SET taken=TRUE,
        timestamp=now()
    FROM (
        SELECT zoid FROM %(qtable)s
        WHERE taken IS FALSE AND finished IS FALSE
        LIMIT 1
    ) AS subquery
    WHERE %(qtable)s.zoid = subquery.zoid
    RETURNING subquery.zoid AS zoid;
    """ % {'qtable': QUEUE_TABLE_NAME}
    try:
        cursor.execute(stmt)
    except (psycopg2.ProgrammingError, psycopg2.InternalError):
        return False
    zoid = None
    for cvalue in cursor:
        zoid = cvalue[0]
    if zoid is None:
        cursor.execute('ABORT;')
        return False  # queue empty
    cursor.execute('COMMIT;')
    log.debug("selected and locked zoid=%s" % zoid)
    return zoid


def _finish_zoid(cursor, zoid):
    stmt = """
    UPDATE %s SET finished=TRUE WHERE zoid=%s;
    COMMIT;
    """ % (QUEUE_TABLE_NAME, zoid)
    try:
        cursor.execute(stmt)
    except psycopg2.InternalError:
        log.warning("hard aborted zoid=%s" % zoid)
    log.debug("finished zoid=%s" % zoid)


def _copy_zoid(cursor, zoid):
    stmt = """
    INSERT INTO %(table)s
        SELECT zoid, tid, state_size, state
        FROM object_state
        WHERE zoid=%(zoid)s
        AND NOT EXISTS (
            SELECT zoid FROM %(table)s
            WHERE zoid = %(zoid)s
        );
    COMMIT;
    """ % {'table': TARGET_TABLE_NAME, 'zoid': zoid}
    try:
        cursor.execute(stmt)
    except:
        log.warning("Statement failed: \n%s" % stmt)
        raise
    log.debug("copied zoid=%s" % zoid)


def _handle_references(cursor, zoid):
    stmt = """
    SELECT state
    FROM object_state
    WHERE zoid=%s;
    """ % (zoid)
    cursor.execute(stmt)
    row = cursor.next()
    if not row:
        log.warning('Can not load state for zoid-%s!' % zoid)
        return
    refs = set(get_references(row[0]))
    if not refs:
        return
    log.debug("handle %s references for zoid=%s" % (len(refs), zoid))
    stmt = ""
    for ref_zoid in refs:
        stmt = """
        INSERT INTO %(qtable)s (zoid)
        SELECT %(zoid)s
        WHERE NOT EXISTS (
            SELECT zoid FROM %(qtable)s
            WHERE zoid = %(zoid)s
        );
        COMMIT;
        """ % {'qtable': QUEUE_TABLE_NAME,
               'ttable': TARGET_TABLE_NAME,
               'zoid': ref_zoid
        }
        try:
            cursor.execute(stmt)
        except:
            log.warning('-> zoid=%s can not be added twice to queue' %
                            ref_zoid)
            raise


def process_queue(cursor):
    """process worker queue
    - fetch an item from queue.
    - for each reference put it in queue.
    - copy item over to new table
    - delete from queue

    return True if item was processed, else False
    """
    start = time.time()
    try:
        zoid = _get_and_lock_next_zoid(cursor)
    except KeyboardInterrupt:
        # conflict - unlock
        cursor.execute('ABORT;')
        log.info(80 * '-' + '\nStopped by human interaction.')
        exit(0)
    except:
        raise
        log.warning(80 * '-' + '\nProblem fetching zoid, wait some millis.')
        time.sleep(0.1)
        return True
    if zoid is False:
        return False
    log.debug('time: % 3.2fms get and lock' % ((time.time() - start) * 1000.0))
    cursor.execute('BEGIN;')
    try:
        middle = time.time()
        _copy_zoid(cursor, zoid)
        log.debug('time: % 3.2fms copy' % ((time.time() - middle) * 1000.0))
        middle = time.time()
        _handle_references(cursor, zoid)
        log.debug('time: % 3.2fms refs' % ((time.time() - middle) * 1000.0))
        middle = time.time()
        _finish_zoid(cursor, zoid)
        log.debug('time: % 3.2fms finish' % ((time.time() - middle) * 1000.0))
    except KeyboardInterrupt:
        # conflict - unlock
        cursor.execute('ABORT;')
        log.info(80 * '-' + '\nStopped by human interaction.')
        exit(0)
    except:
        # conflict - unlock
        cursor.execute('ABORT;')
        log.warning(80 * '-' + '\nAbort for unknown reason, wait some millis.')
        time.sleep(0.1)
        return True
    log.info('processed item %s in % 3.2fms' %
              (zoid, (time.time() - start) * 1000.0))
    return True


def run(argv=sys.argv):
    log.info("Packing worker started")
    storage = get_storage(argv, __doc__, False)
    try:
        while True:
            state = dbop(storage, process_queue)
            if not state:
                log.info("Nothing to do, check again in %ss" % EMTPY_DELAY)
                time.sleep(EMTPY_DELAY)
    finally:
        log.info("Closing storage")
        storage.close()
        log.info("Packing worker stopped")
