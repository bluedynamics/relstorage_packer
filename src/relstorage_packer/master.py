"""relstorage_packer - master process"""
import logging
import sys
import time
from .utils import dbop
from .utils import get_storage
from .utils import QUEUE_TABLE_NAME
from .worker import process_queue

WAIT_DELAY = 2

log = logging.getLogger("relstorage_packer:master")


def aquire_master_lock(cursor):
    """try to acquire a master lock, if not possible log error and exit with 1
    """
    log.info("Acquiring master lock")
    pass


def release_master_lock(cursor):
    """release master lock
    """
    log.info("Releasing master lock")


def queue_root(cursor):
    """queue ZODB root node, which has always zoid=0
    """
    log.info("Queuing ZODB root node")
    stmt = "INSERT INTO %s values(0);" % QUEUE_TABLE_NAME
    cursor.execute(stmt)
    return


def get_queue_count(cursor):
    stmt = "SELECT COUNT(*) FROM %s;" % QUEUE_TABLE_NAME
    cursor.execute(stmt)
    for (name,) in cursor:
        return name
    return -1


def finalize_pack(cursor):
    log.info("Finalizing packing")
    pass


def run(argv=sys.argv):
    log.info("Initiating packing.")
    storage = get_storage(argv, __doc__, True)
    if storage.master_initialize:
        try:
            dbop(storage, aquire_master_lock)
            dbop(storage, queue_root)
        except:
            dbop(storage, release_master_lock)
            storage.close()
            raise
    # TODO: Remember transaction id persistent!
    try:
        queue_count = dbop(storage, get_queue_count)
        while queue_count:
            logging.info("waiting %ss - queue count %d" % \
                         (WAIT_DELAY, queue_count))
            time.sleep(WAIT_DELAY)
            queue_count = dbop(storage, get_queue_count)

    except:
        dbop(storage, release_master_lock)
        storage.close()
        raise
    log.info("Queue Empty")
    try:
        dbop(storage, finalize_pack)
    except:
        dbop(storage, release_master_lock)
        storage.close()
        raise

    log.info("Packing finished")


if __name__ == '__main__':
    main()
