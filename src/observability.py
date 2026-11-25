"""Central log/span collector. Own DB; reads no business database."""
import json
import time
from .common import Service, internal, require, text_field, Problem


class Observability(Service):
    def __init__(self):
        super().__init__('observability')
        self.db.schema('''CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,
            time REAL NOT NULL,node TEXT,instance TEXT,trace_id TEXT,event TEXT,body TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS record_trace ON records(trace_id,id);''')

    def dispatch(self, method, path, body, headers, corr):
        internal(headers)
        if method=='POST' and path=='/records':
            records=body.get('records')
            require(isinstance(records,list) and 1<=len(records)<=40,400,'Invalid log batch')
            with self.db.tx() as db:
                for record in records:
                    require(isinstance(record,dict) and type(record.get('time_unix')) in (int,float),400,'Invalid log record')
                    for key in ('node','instance','event'):
                        text_field(record,key,1,128)
                    encoded=json.dumps(record,allow_nan=False)
                    require(len(encoded)<8000,413,'Log record too large')
                    db.execute('INSERT INTO records(time,node,instance,trace_id,event,body) VALUES(?,?,?,?,?,?)',
                               (record['time_unix'],record['node'],record['instance'],record.get('trace_id',record.get('correlation_id')),
                                record['event'],encoded))
                db.execute('DELETE FROM records WHERE id < (SELECT COALESCE(MAX(id),0)-50000 FROM records)')
            return {'stored':len(records)}
        if method=='GET' and path=='/logs':
            with self.db.connect() as db:
                return {'records':[json.loads(r['body']) for r in db.execute('SELECT body FROM records ORDER BY id DESC LIMIT 100')]}
        if method=='GET' and path=='/traces':
            with self.db.connect() as db:
                return {'traces':[dict(r) for r in db.execute("SELECT trace_id,MIN(time) AS started,MAX(time) AS updated,"
                    "COUNT(*) AS records,COUNT(DISTINCT node) AS services FROM records WHERE trace_id IS NOT NULL "
                    "AND trace_id!='-' GROUP BY trace_id HAVING COUNT(DISTINCT node)>1 ORDER BY updated DESC LIMIT 50")]}
        if method=='GET' and path=='/instances':
            with self.db.connect() as db:
                rows=[dict(r) for r in db.execute('SELECT node,instance,MAX(time) AS last_seen,COUNT(*) AS records FROM records GROUP BY node,instance')]
            for row in rows:
                row['status']='online' if time.time()-row['last_seen']<35 else 'stale'
            return {'instances':rows}
        if method=='GET' and path.startswith('/traces/'):
            trace=path.split('/')[-1]
            with self.db.connect() as db:
                rows=db.execute('SELECT body FROM records WHERE trace_id=? ORDER BY time,id LIMIT 500',(trace,)).fetchall()
            return {'trace_id':trace,'records':[json.loads(r['body']) for r in rows]}
        raise Problem(404,'Route not found')
