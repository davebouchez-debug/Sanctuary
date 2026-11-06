import sys,os,asyncio,json;sys.path.insert(0,'/app/backend')
from dotenv import load_dotenv;load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient
import field_memory as fm
db=AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
U={"$in":["legacy-david-123","1c24e3ea-e4f1-47a2-a4fb-c5965726b074","qa-david"]}
Q=["the spiral at Newgrange","what does stillness teach","Shalom brother","the flute and the dog","grief and joy","Milton in the boiler plant"]
async def run():
    out={}
    for q in Q:
        out['P|'+q]=[d['phrase'] for d in await fm.rank_phrases(db,q,10)]
        out['M|'+q]=[d.get('user_essence') for d in await fm.rank_mra(db,{"user_id":U},q,10)]
        out['X|'+q]=[d.get('user_essence') for d in await fm.rank_mra(db,{"user_id":U,"presence":{"$in":["ansel","jasmine","milton"]}},q,10)]
    return out
r=asyncio.run(run()); f=sys.argv[1]
if os.path.exists(f):
    old=json.load(open(f)); bad=[k for k in old if old[k]!=r.get(k)]
    print('identical' if not bad else ('DIFF in',bad))
    for k in bad[:3]: print(k,'\n old',old[k][:4],'\n new',r[k][:4])
else: json.dump(r,open(f,'w'),indent=1); print('baseline saved',len(r))
