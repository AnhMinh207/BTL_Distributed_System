"""Independent, idempotent fare quotes with demand-based surge."""
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from .common import Service, actor, internal, coordinates, require, call, service_url, internal_headers, distance, uid


class Pricing(Service):
    def __init__(self):
        super().__init__('pricing')
        self.db.schema('''CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,
            response TEXT NOT NULL,created REAL NOT NULL);''')

    def dispatch(self,method,path,body,headers,corr):
        require(method=='POST' and path in ('/quote','/internal/quote'),404,'Route not found')
        internal(headers) if path.startswith('/internal/') else actor(headers)
        pickup,destination=coordinates(body,'pickup'),coordinates(body,'destination')
        quote_key=body.get('quote_key') if path.startswith('/internal/') else uid()
        require(isinstance(quote_key,str) and 1<=len(quote_key)<=256,400,'Invalid quote key')
        fingerprint=hashlib.sha256(json.dumps([pickup,destination]).encode()).hexdigest()
        with self.db.connect() as db:
            old=db.execute('SELECT * FROM quotes WHERE id=?',(quote_key,)).fetchone()
        if old:
            require(old['fingerprint']==fingerprint,409,'Quote key conflict')
            return json.loads(old['response'])
        def load(service,route):
            return call(service_url(service)+route,'POST',{'pickup':pickup},
                        {**internal_headers(),'X-Correlation-ID':corr},timeout=.8)[1]
        with ThreadPoolExecutor(2) as pool:
            supply=pool.submit(copy_context().run,load,'driver','/internal/supply')
            demand=pool.submit(copy_context().run,load,'trip','/internal/demand')
            degraded=[]
            try:
                available=supply.result()['available']
            except Exception:
                available=0;degraded.append('driver')
            try:
                waiting=demand.result()['waiting']
            except Exception:
                waiting=0;degraded.append('trip')
        # Never surge on unknown supply/demand; allow the queue/Saga to handle matching outages.
        if degraded:
            waiting=0
        multiplier=min(2.0,1.0+.25*max(0,waiting-available)) if os.getenv('DYNAMIC_PRICING','1')=='1' else 1.0
        km=distance(pickup,destination)
        base=12000+round(km*8000)
        result=dict(quote_id=quote_key,base_fare=base,fare=round(base*multiplier),multiplier=multiplier,
                    distance_km=round(km,3),available_drivers=available,waiting_requests=waiting,
                    currency='VND',calculated_at=time.time())
        result['degraded_dependencies']=degraded
        with self.db.tx() as db:
            db.execute('INSERT OR IGNORE INTO quotes VALUES(?,?,?,?)',(quote_key,fingerprint,json.dumps(result),time.time()))
            row=db.execute('SELECT * FROM quotes WHERE id=?',(quote_key,)).fetchone()
            require(row['fingerprint']==fingerprint,409,'Quote key conflict')
            return json.loads(row['response'])
