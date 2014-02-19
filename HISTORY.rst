
History
=======

2.1 (2014-02-19)
----------------

- refactored logging, because it was always in my way when changing other parts 
  of the code.
  [jensens, 2014-02-19]

- after long running connections postgresql takes lots of RAM. So we reconnect
  every 5000 cycles (TID analyzing or ZOID removal).
  [jensens, 2014-02-18]

- we had a whole bunch of ``idle in transaction (aborted)`` postgres
  processes running after packing. This resulted in in an ``OperationalError:
  out of shared memory HINT: You might need to increase
  max_pred_locks_per_transaction.`` Error. As a result I refactored the
  transaction handling and rollback and use explicit commit instead of using
  the relstorage ``storage._with_store``. Now this part is very controlled
  and not the source of hanging connections w/o rollback.
  [jensens, 2014-02-18]


2.0.2 (2014-02-05)
------------------

- also support storages w/o blobstorage
  [jensens, 2014-02-05]


2.0.1 (2014-02-03)
------------------

- unlock in a finally to really unlock an failure
  [jensens, 2014-02-03]

- use non-zero exit code if lock could not be aquired.
  [saily]


2.0
---

- refactored the way of collecting and using the reference counts. faster now.
  [jensens, 2014-01-11]

1.0
---

- started package
  [jensens, 2013-11-23]
