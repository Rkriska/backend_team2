from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.models import Distance,VectorParams,PointStruct,Filter,FilterSelector,FieldCondition,MatchValue
from app.config import settings
VECTOR_SIZE=768
@lru_cache
def get_qdrant_client():
 kwargs={'url':settings.QDRANT_URL}
 if settings.QDRANT_API_KEY: kwargs['api_key']=settings.QDRANT_API_KEY
 return QdrantClient(**kwargs)
def collection_exists(name:str)->bool: return get_qdrant_client().collection_exists(name)
def ensure_collection(collection_name:str,vector_size:int=VECTOR_SIZE):
 c=get_qdrant_client()
 if not c.collection_exists(collection_name): c.create_collection(collection_name=collection_name,vectors_config=VectorParams(size=vector_size,distance=Distance.COSINE))
def upsert_points(collection_name:str,points:list[dict]):
 if not points:return
 ensure_collection(collection_name)
 get_qdrant_client().upsert(collection_name=collection_name,points=[PointStruct(id=p['id'],vector=p['vector'],payload=p.get('payload',{})) for p in points],wait=True)
def search_points(collection_name:str,query_vector:list[float],limit:int=5,filter_payload:dict|None=None)->list[dict]:
 c=get_qdrant_client()
 if not c.collection_exists(collection_name): return []
 f=Filter(must=[FieldCondition(key=k,match=MatchValue(value=v)) for k,v in filter_payload.items()]) if filter_payload else None
 return [{'id':str(x.id),'score':x.score,'payload':x.payload or {}} for x in c.search(collection_name=collection_name,query_vector=query_vector,query_filter=f,limit=limit,with_payload=True)]
def delete_points_by_payload(collection_name:str,document_id:str):
 c=get_qdrant_client()
 if c.collection_exists(collection_name): c.delete(collection_name=collection_name,points_selector=FilterSelector(filter=Filter(must=[FieldCondition(key='document_id',match=MatchValue(value=document_id))])),wait=True)
def delete_collection(collection_name:str):
 c=get_qdrant_client()
 if c.collection_exists(collection_name): c.delete_collection(collection_name)
