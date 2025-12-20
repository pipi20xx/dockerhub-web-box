from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ....database import crud
from ....database.database import get_db
from ....schemas import proxy as schema

router = APIRouter()

@router.get("/", response_model=List[schema.Proxy])
def read_proxies(db: Session = Depends(get_db)):
    return crud.get_proxies(db)

@router.post("/", response_model=schema.Proxy, status_code=201)
def create_proxy(proxy: schema.ProxyCreate, db: Session = Depends(get_db)):
    if crud.get_proxy_by_name(db, name=proxy.name):
        raise HTTPException(status_code=400, detail="代理名称已存在")
    return crud.create_proxy(db, proxy)

@router.put("/{proxy_id}", response_model=schema.Proxy)
def update_proxy(proxy_id: str, proxy_in: schema.ProxyUpdate, db: Session = Depends(get_db)):
    db_proxy = crud.get_proxy(db, proxy_id)
    if not db_proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
        
    if proxy_in.name and proxy_in.name != db_proxy.name:
         if crud.get_proxy_by_name(db, name=proxy_in.name):
             raise HTTPException(status_code=400, detail="Proxy name already exists")
             
    return crud.update_proxy(db=db, db_proxy=db_proxy, proxy_in=proxy_in)

@router.delete("/{proxy_id}", status_code=204)
def delete_proxy(proxy_id: str, db: Session = Depends(get_db)):
    db_proxy = crud.get_proxy(db, proxy_id)
    if not db_proxy:
        raise HTTPException(status_code=404, detail="代理未找到")
    crud.delete_proxy(db, db_proxy)
    return None

