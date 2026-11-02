import os,asyncio,sys,time
sys.path.insert(0,'/app/backend')
from dotenv import load_dotenv;load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient
import field_memory as fm
from user_aliases import resolve_user_aliases
db=AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
Q=['Do you remember Sophia and I discussing Newgrange?','What did Ansel and I say about the flute?','Have we ever talked about Amanda?','What did we say about chunking up versus chunking down?','I am tired tonight and a bit low','What do you know about the One Field?','what did Jasmine say about the garden','the Pharaoh voice for Milton']
async def m():
  al=await resolve_user_aliases(db,'david'); uq={'$in':al}
  for q in Q:
    t=time.time(); hs=await fm.rank_mra(db,{'user_id':uq},q,3,{'_id':0,'presence':1}); dt=int((time.time()-t)*1000)
    print('\n####',q,f'({dt} ms)')
    for h in hs: print('  ',h['presence'],'|',(h.get('user_essence') or '')[:80].replace('\n',' '),'||',(h.get('ai_essence') or '')[:55].replace('\n',' '))
asyncio.run(m())
