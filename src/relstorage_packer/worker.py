import logging
import sys
import time
from .utils import dbop
from .utils import get_references
from .utils import get_storage
from .utils import QUEUE_TABLE_NAME
from .utils import TARGET_TABLE_NAME

EMTPY_DELAY = 10


def _get_and_lock_next_zoid(cursor):
    # select lowest zoid for update
    stmt = """
    SELECT zoid FROM %s
    WHERE taken IS FALSE
    ORDER BY zoid
    LIMIT 1
    FOR UPDATE;
    """ % QUEUE_TABLE_NAME
    cursor.execute(stmt)
    zoids = [_[0] for _ in cursor]
    if not zoids:
        return False  # queue empty
    zoid = zoids[0]
    stmt = """
    UPDATE %s
    SET taken=TRUE,
        timestamp=now()
    WHERE zoid=%s;
    COMMIT;
    BEGIN;
    """ % (QUEUE_TABLE_NAME, zoid)
    cursor.execute(stmt)
    logging.info("selected and locked zoid=%s" % zoid)
    return zoid


def _finish_zoid(cursor, zoid):
    stmt = """
    DELETE FROM %s WHERE zoid=%s;
    COMMIT;
    """ % (QUEUE_TABLE_NAME, zoid)
    cursor.execute(stmt)
    logging.info("finished zoid=%s" % zoid)


def _copy_zoid(cursor, zoid):
    stmt = """
    INSERT INTO %s
        SELECT zoid, tid, state_size, state
        FROM object_state
        WHERE zoid=%s;
    """ % (TARGET_TABLE_NAME, zoid)
    cursor.execute(stmt)
    logging.info("copied zoid=%s" % zoid)


def _handle_references(cursor, zoid):
    stmt = """
    SELECT state
    FROM object_state
    WHERE zoid=%s;
    """ % (zoid)
    cursor.execute(stmt)
    row = cursor.next()
    if not row:
        logging.error('Can not load state!')
        return
    refs = get_references(row[0])
    logging.info("handle %s references for zoid=%s" % (len(refs), zoid))
    stmt = ""
    for ref_zoid in refs:
        stmt += "INSERT INTO %s values(%s);" % (QUEUE_TABLE_NAME, ref_zoid)
    if stmt:
        cursor.execute(stmt)


def process_queue(cursor):
    """process worker queue
    - fetch an item from queue.
    - for each reference put it in queue.
    - copy item over to new table
    - delete from queue

    return True if item was processed, else False
    """
    zoid = _get_and_lock_next_zoid(cursor)
    if zoid is False:
        return False
    _copy_zoid(cursor, zoid)
    _handle_references(cursor, zoid)
    _finish_zoid(cursor, zoid)
    return True


def run(argv=sys.argv):
    logging.info("Packing worker started")
    storage = get_storage(argv, __doc__, False)
    try:
        while True:
            state = dbop(storage, process_queue)
            if not state:
                logging.info("Nothing to do, check again in %ss" % EMTPY_DELAY)
                time.sleep(EMTPY_DELAY)
    finally:
        logging.info("Closing storage")
        storage.close()
        logging.info("Packing worker stopped")
