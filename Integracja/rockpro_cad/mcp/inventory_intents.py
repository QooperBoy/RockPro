"""Durable operator requests; preparing/cancelling never changes physical stock.

Inventory execution and the committed marker share one SQLite transaction.
Transport errors leave a discoverable request rather than inventing a new ID.
"""
import json
import sqlite3
import inventory_service as inventory
import project_store as store
from material_service import digest,encode,token

STATES={'prepared','committed','rejected','cancelled'}


def ensure(conn):
    inventory.ensure(conn)
    conn.execute('''CREATE TABLE IF NOT EXISTS inventory_intents(
        operation_id TEXT PRIMARY KEY,command_json TEXT NOT NULL,command_sha256 TEXT NOT NULL,
        expected_revision INTEGER NOT NULL,state TEXT NOT NULL,
        created_at TEXT NOT NULL,updated_at TEXT NOT NULL,actor TEXT NOT NULL,
        decision_reference TEXT NOT NULL,diagnostic TEXT)''')


def _verify(row):
    try:
        command=json.loads(row['command_json'])
        if (not isinstance(command,dict) or row['state'] not in STATES or
            type(row['expected_revision']) is not int or row['expected_revision']<0 or
            digest(dict(command=command,expected_revision=row['expected_revision']))!=row['command_sha256']):
            raise ValueError('Request differs from its binding')
    except (ValueError,TypeError) as error:
        raise ValueError('INVENTORY_INTENT_INTEGRITY') from error
    return command


def _row(conn,operation_id):
    row=conn.execute('SELECT * FROM inventory_intents WHERE operation_id=?',(operation_id,)).fetchone()
    if row is None:raise ValueError('INVENTORY_INTENT_NOT_FOUND')
    return row


def _result(conn,row):
    command=_verify(row)
    receipt=conn.execute('SELECT * FROM inventory_journal WHERE operation_id=?',(row['operation_id'],)).fetchone()
    if (row['state']=='committed')!=(receipt is not None):raise ValueError('INVENTORY_INTENT_INTEGRITY: journal/state mismatch')
    if receipt is not None and receipt['command_sha256']!=row['command_sha256']:raise ValueError('INVENTORY_INTENT_INTEGRITY: command mismatch')
    return dict(operation_id=row['operation_id'],command=command,command_sha256=row['command_sha256'],
        expected_revision=row['expected_revision'],state=row['state'],created_at=row['created_at'],updated_at=row['updated_at'],
        actor=row['actor'],decision_reference=row['decision_reference'],diagnostic=row['diagnostic'],
        receipt=inventory._receipt(receipt) if receipt is not None else None,identity_verified=False,production_approved=False)


def guard_intent(conn,operation_id,command_sha256):
    """Called inside the stock transaction, including legacy direct execution."""
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='inventory_intents'").fetchone() is None:return None
    row=conn.execute('SELECT * FROM inventory_intents WHERE operation_id=?',(operation_id,)).fetchone()
    if row is None:return None
    _result(conn,row)
    if row['command_sha256']!=command_sha256:raise ValueError('INVENTORY_OPERATION_ID_REUSED')
    if row['state'] not in ('prepared','committed'):raise ValueError('INVENTORY_INTENT_TERMINAL: '+row['state'])
    return row


def prepare_inventory_command(command,operation_id,expected_revision,decision_reference,actor='UI'):
    token(operation_id,'operation ID')
    if type(expected_revision) is not int or expected_revision<0:raise ValueError('Inventory expected_revision required')
    # This validates the request shape, not the future availability of stock.
    if (not isinstance(command,dict) or command.get('action') not in inventory.COMMAND_FIELDS or
        set(command)!=inventory.COMMAND_FIELDS[command['action']]):
        raise ValueError('Unknown inventory action/fields')
    payload=encode(command)
    if len(payload.encode('utf-8'))>65536:raise ValueError('Inventory request too large')
    actor=store.text(actor,'actor',200);reference=store.text(decision_reference,'decision reference',1000)
    if not reference:raise ValueError('Explicit decision reference required')
    binding=digest(dict(command=command,expected_revision=expected_revision))
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');ensure(conn)
        previous=conn.execute('SELECT * FROM inventory_intents WHERE operation_id=?',(operation_id,)).fetchone()
        if previous is not None:
            if previous['command_sha256']!=binding or previous['actor']!=actor or previous['decision_reference']!=reference:
                raise ValueError('INVENTORY_OPERATION_ID_REUSED')
            return _result(conn,previous)
        if conn.execute('SELECT 1 FROM inventory_journal WHERE operation_id=?',(operation_id,)).fetchone():
            raise ValueError('INVENTORY_OPERATION_ALREADY_COMMITTED')
        stamp=store.now()
        conn.execute('INSERT INTO inventory_intents VALUES(?,?,?,?,?,?,?,?,?,NULL)',
            (operation_id,payload,binding,expected_revision,'prepared',stamp,stamp,actor,reference))
        return _result(conn,_row(conn,operation_id))


def get_inventory_intent(operation_id):
    token(operation_id,'operation ID')
    with store.db() as conn:
        conn.execute('BEGIN');ensure(conn)
        return _result(conn,_row(conn,operation_id))


def list_inventory_intents(state='prepared',limit=100):
    if state not in STATES|{'all'}:raise ValueError('Explicit inventory intent state required')
    if type(limit) is not int or not 1<=limit<=100:raise ValueError('Inventory intent limit 1..100 required')
    with store.db() as conn:
        conn.execute('BEGIN');ensure(conn)
        rows=conn.execute('SELECT * FROM inventory_intents WHERE (?=\'all\' OR state=?) ORDER BY created_at DESC,rowid DESC LIMIT ?',
                          (state,state,limit)).fetchall()
        return dict(intents=[_result(conn,row) for row in rows],state=state,limit=limit,production_approved=False)


def execute_inventory_intent(operation_id):
    prepared=get_inventory_intent(operation_id)
    if prepared['state'] not in ('prepared','committed'):raise ValueError('INVENTORY_INTENT_TERMINAL: '+prepared['state'])
    try:
        inventory.inventory_command(prepared['command'],operation_id,prepared['expected_revision'])
    except (ValueError,sqlite3.IntegrityError) as error:
        # A definite business rejection rolled back the stock transaction. An
        # unknown/transport failure is not classified here and retains its ID.
        with store.db() as conn:
            conn.execute('BEGIN IMMEDIATE');ensure(conn)
            current=_row(conn,operation_id);_verify(current)
            receipt=conn.execute('SELECT 1 FROM inventory_journal WHERE operation_id=?',(operation_id,)).fetchone()
            if current['state']=='prepared' and receipt is None:
                conn.execute("UPDATE inventory_intents SET state='rejected',diagnostic=?,updated_at=? WHERE operation_id=?",
                             (str(error)[:1000],store.now(),operation_id))
        raise
    return get_inventory_intent(operation_id)


def cancel_inventory_intent(operation_id,command_sha256):
    token(operation_id,'operation ID')
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');ensure(conn);row=_row(conn,operation_id);result=_result(conn,row)
        if row['command_sha256']!=command_sha256:raise ValueError('INVENTORY_RECEIPT_COMMAND_MISMATCH')
        if row['state']=='cancelled':return result
        if row['state']!='prepared':raise ValueError('INVENTORY_INTENT_TERMINAL: '+row['state'])
        conn.execute("UPDATE inventory_intents SET state='cancelled',updated_at=? WHERE operation_id=?",(store.now(),operation_id))
        return _result(conn,_row(conn,operation_id))
