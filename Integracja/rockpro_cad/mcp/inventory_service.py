"""ROC-31: transactional lots, offcuts, holds, issues, returns and deliveries.

One physical balance: holds reduce availability, issues reduce on-hand and end
the hold. Consuming issued stock changes history, never subtracts it twice.
"""
from datetime import date
import json
import project_store as store
from material_service import digest, encode, positive, token


def ensure(conn):
    statements=[
        '''CREATE TABLE IF NOT EXISTS inventory_lots(id TEXT PRIMARY KEY, data_json TEXT NOT NULL,
           on_hand INTEGER NOT NULL CHECK(on_hand>=0), revision INTEGER NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS inventory_reservations(id TEXT PRIMARY KEY,
           lot_id TEXT NOT NULL REFERENCES inventory_lots(id), plan_id TEXT NOT NULL,
           quantity INTEGER NOT NULL, status TEXT NOT NULL, returned INTEGER NOT NULL DEFAULT 0)''',
        '''CREATE TABLE IF NOT EXISTS inventory_deliveries(id TEXT PRIMARY KEY,data_json TEXT NOT NULL,
           received INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS inventory_journal(operation_id TEXT PRIMARY KEY,
           command_sha256 TEXT NOT NULL,result_json TEXT NOT NULL,created_at TEXT NOT NULL)'''
    ]
    for statement in statements:conn.execute(statement)


def quantity(value):
    if type(value) is not int or not 1<=value<=1000000:raise ValueError('Positive integer inventory quantity required')
    return value


def validate_lot(lot):
    if not isinstance(lot,dict) or set(lot)!={'id','item_id','unit','location','on_hand','dimensions_mm','condition','scope'}:
        raise ValueError('Exact inventory lot fields required')
    for k in ('id','item_id','location'):token(lot[k],k)
    if lot['unit'] not in ('piece','sheet','offcut') or lot['condition'] not in ('usable','quarantine','scrap'):
        raise ValueError('Explicit inventory unit and physical condition required')
    if lot['scope'] not in ('source_input','synthetic_test'):raise ValueError('Inventory scope required')
    quantity(lot['on_hand'])
    dimensions=lot['dimensions_mm']
    if lot['unit']=='piece':
        if dimensions is not None:raise ValueError('Piece dimensions must be null; sheet/offcut require explicit dimensions')
    else:
        if not isinstance(dimensions,list) or len(dimensions)!=3:raise ValueError('Sheet/offcut L W thickness required')
        for n in dimensions:positive(n,'stock dimension',10000)
        if lot['unit']=='offcut' and lot['on_hand']!=1:raise ValueError('Each physical offcut needs a unique lot ID')


def _balance(conn, ident):
    row=conn.execute('SELECT * FROM inventory_lots WHERE id=?',(ident,)).fetchone()
    if row is None:raise ValueError('INVENTORY_LOT_NOT_FOUND')
    result=json.loads(row['data_json'])
    held=conn.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_reservations WHERE lot_id=? AND status='held'",(ident,)).fetchone()[0]
    return result|dict(on_hand=row['on_hand'],revision=row['revision'],reserved=held,
                       free=row['on_hand']-held if result['condition']=='usable' else 0)


def inventory_command(command, operation_id, expected_revision):
    token(operation_id,'operation ID')
    if type(expected_revision) is not int or expected_revision<0:raise ValueError('Inventory expected_revision required')
    if not isinstance(command,dict):raise ValueError('Inventory command required')
    action=command.get('action')
    fields={'register':{'action','lot'},'reserve':{'action','lot_id','reservation_id','plan_id','quantity'},
            'issue':{'action','reservation_id'},'cancel':{'action','reservation_id'},
            'consume':{'action','reservation_id'},'return':{'action','reservation_id','quantity'},
            'delivery':{'action','delivery'},'receive':{'action','delivery_id','lot'}}
    if action not in fields or set(command)!=fields[action]:raise ValueError('Unknown inventory action/fields')
    command_hash=digest(dict(command=command,expected_revision=expected_revision))
    with store.db() as conn:
        conn.execute('BEGIN IMMEDIATE');ensure(conn)
        previous=conn.execute('SELECT * FROM inventory_journal WHERE operation_id=?',(operation_id,)).fetchone()
        if previous:
            if previous['command_sha256']!=command_hash:raise ValueError('INVENTORY_OPERATION_ID_REUSED')
            return json.loads(previous['result_json'])|dict(replayed=True)
        if action in ('register','receive'):
            lot=command['lot'];validate_lot(lot)
            if action=='register':
                if expected_revision!=0:raise ValueError('INVENTORY_REVISION_CONFLICT')
            else:
                delivery=conn.execute('SELECT * FROM inventory_deliveries WHERE id=?',(command['delivery_id'],)).fetchone()
                if delivery is None:raise ValueError('DELIVERY_NOT_FOUND')
                if delivery['revision']!=expected_revision:raise ValueError('DELIVERY_REVISION_CONFLICT')
                data=json.loads(delivery['data_json'])
                if any(data[k]!=lot[k] for k in ('item_id','unit','scope')) or lot['on_hand']>data['quantity']-delivery['received']:
                    raise ValueError('Delivery receipt does not match remaining confirmed supply')
                conn.execute('UPDATE inventory_deliveries SET received=received+?,revision=revision+1 WHERE id=?',(lot['on_hand'],command['delivery_id']))
            conn.execute('INSERT INTO inventory_lots VALUES (?,?,?,1)',(lot['id'],encode(lot),lot['on_hand']))
            result=dict(lot=_balance(conn,lot['id']))
        elif action=='delivery':
            d=command['delivery']
            if not isinstance(d,dict) or set(d)!={'id','item_id','unit','quantity','due_date','confirmation_reference','scope'}:raise ValueError('Exact confirmed delivery fields required')
            for k in ('id','item_id','confirmation_reference'):token(d[k],k)
            quantity(d['quantity'])
            if d['unit'] not in ('piece','sheet','offcut') or d['scope'] not in ('source_input','synthetic_test'):raise ValueError('Delivery unit/scope required')
            if date.fromisoformat(d['due_date']).isoformat()!=d['due_date']:raise ValueError('ISO delivery date required')
            if expected_revision!=0:raise ValueError('DELIVERY_REVISION_CONFLICT')
            conn.execute('INSERT INTO inventory_deliveries VALUES (?,?,0,1)',(d['id'],encode(d)))
            result=dict(delivery=d|dict(received=0,revision=1))
        else:
            reservation=None
            if action=='reserve':
                for k in ('lot_id','reservation_id','plan_id'):token(command[k],k)
                ident=command['lot_id']
            else:
                token(command['reservation_id'],'reservation ID')
                reservation=conn.execute('SELECT * FROM inventory_reservations WHERE id=?',(command['reservation_id'],)).fetchone()
                if reservation is None:raise ValueError('RESERVATION_NOT_FOUND')
                ident=reservation['lot_id']
            before=_balance(conn,ident)
            if before['revision']!=expected_revision:raise ValueError('INVENTORY_REVISION_CONFLICT')
            if action=='reserve':
                n=quantity(command['quantity'])
                if before['free']<n:raise ValueError('INSUFFICIENT_FREE_STOCK')
                conn.execute('INSERT INTO inventory_reservations VALUES (?,?,?,?,?,0)',
                             (command['reservation_id'],ident,command['plan_id'],n,'held'))
            elif action in ('cancel','issue'):
                if reservation['status']!='held':raise ValueError('Only an unissued hold can be cancelled/issued')
                if action=='issue':
                    if before['condition']!='usable':raise ValueError('Stock is not usable')
                    conn.execute('UPDATE inventory_lots SET on_hand=on_hand-? WHERE id=?',(reservation['quantity'],ident))
                conn.execute('UPDATE inventory_reservations SET status=? WHERE id=?',('issued' if action=='issue' else 'cancelled',reservation['id']))
            elif action=='consume':
                if reservation['status']!='issued':raise ValueError('Only issued stock can be consumed')
                conn.execute("UPDATE inventory_reservations SET status='consumed' WHERE id=?",(reservation['id'],))
            else:
                n=quantity(command['quantity'])
                if reservation['status']!='issued' or n>reservation['quantity']-reservation['returned']:raise ValueError('Only unconsumed issued quantity can be returned')
                returned=reservation['returned']+n
                conn.execute('UPDATE inventory_reservations SET returned=?,status=? WHERE id=?',
                    (returned,'returned' if returned==reservation['quantity'] else 'issued',reservation['id']))
                conn.execute('UPDATE inventory_lots SET on_hand=on_hand+? WHERE id=?',(n,ident))
            conn.execute('UPDATE inventory_lots SET revision=revision+1 WHERE id=?',(ident,))
            result=dict(lot=_balance(conn,ident),reservation=dict(conn.execute('SELECT * FROM inventory_reservations WHERE id=?',(command['reservation_id'],)).fetchone()))
        result.update(operation_id=operation_id,action=action,replayed=False,identity_verified=False,production_approved=False)
        conn.execute('INSERT INTO inventory_journal VALUES (?,?,?,?)',(operation_id,command_hash,encode(result),store.now()))
    return result


def get_inventory():
    with store.db() as conn:
        conn.execute('BEGIN');ensure(conn)
        ids=[r[0] for r in conn.execute('SELECT id FROM inventory_lots ORDER BY id LIMIT 1001')]
        if len(ids)>1000:raise ValueError('Inventory listing exceeds 1000 lots; add pagination before expansion')
        lots=[_balance(conn,i) for i in ids]
        reservations=[dict(r) for r in conn.execute('SELECT * FROM inventory_reservations ORDER BY id')]
        deliveries=[json.loads(r['data_json'])|dict(received=r['received'],revision=r['revision'],outstanding=json.loads(r['data_json'])['quantity']-r['received'])
                    for r in conn.execute('SELECT * FROM inventory_deliveries ORDER BY id')]
    return dict(lots=lots,reservations=reservations,deliveries=deliveries,production_approved=False)


def get_inventory_history(limit=100):
    if type(limit) is not int or not 1<=limit<=500:raise ValueError('History limit 1..500 required')
    with store.db() as conn:
        ensure(conn);rows=[dict(r) for r in conn.execute('SELECT * FROM inventory_journal ORDER BY created_at DESC,operation_id DESC LIMIT ?',(limit,))]
    return dict(events=[dict(operation_id=r['operation_id'],created_at=r['created_at'],command_sha256=r['command_sha256'],result=json.loads(r['result_json'])) for r in rows])
