import logging
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


def dbop(storage, func, *args, **kwargs):
    """wrapper to private method in order to call a given function with
    connection, cursor and optionally given args and kwargs.
    """

    def func_conn(conn, cursor, *args, **kwargs):
        return func(conn, cursor, *args, **kwargs)

    return storage._with_store(func_conn, *args, **kwargs)


def get_storage(config_file):
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
    return storage


def get_references(state):
    """Return the set of OIDs the given state refers to."""
    refs = set()
    if state:
        for oid in referencesf(str(state)):
            refs.add(u64(oid))
    return refs
