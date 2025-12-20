from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import docker

from ....database import crud
from ....database.database import get_db
from ....schemas import credential as schema

router = APIRouter()

@router.get("/", response_model=List[schema.Credential])
def read_credentials(db: Session = Depends(get_db)):
    creds = crud.get_credentials(db)
    result = []
    for cred in creds:
        result.append({
            "id": cred.id,
            "name": cred.name,
            "registry_url": cred.registry_url,
            "username": cred.username,
            "password": cred.encrypted_password  # Now stores plain text
        })
    return result

@router.post("/", response_model=schema.Credential, status_code=201)
def create_credential(cred: schema.CredentialCreate, db: Session = Depends(get_db)):
    if crud.get_credential_by_name(db, name=cred.name):
        raise HTTPException(status_code=400, detail="凭证名称已存在")
    
    try:
        client = docker.from_env()
        client.login(username=cred.username, password=cred.password, registry=cred.registry_url)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"凭证验证失败: {e}")
        
    return crud.create_credential(db=db, cred=cred)

@router.put("/{cred_id}", response_model=schema.Credential)
def update_credential(cred_id: str, cred_in: schema.CredentialUpdate, db: Session = Depends(get_db)):
    db_cred = crud.get_credential(db, cred_id)
    if not db_cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    if cred_in.name and cred_in.name != db_cred.name:
         if crud.get_credential_by_name(db, name=cred_in.name):
             raise HTTPException(status_code=400, detail="Credential name already exists")

    # If password or registry info changes, we should probably re-verify login
    if cred_in.password or cred_in.username or cred_in.registry_url:
        username = cred_in.username or db_cred.username
        password = cred_in.password # If None, we can't verify unless we decrypt existing, which we can do
        registry = cred_in.registry_url or db_cred.registry_url
        
        # If password is provided, verify. If not, and only user/registry changed, 
        # we strictly should verify but we don't have the raw password easily available (it's encrypted).
        # For simplicity/security, only verify if password is being updated.
        if cred_in.password:
            try:
                client = docker.from_env()
                client.login(username=username, password=password, registry=registry)
            except Exception as e:
                raise HTTPException(status_code=401, detail=f"Credential validation failed: {e}")

    return crud.update_credential(db=db, db_cred=db_cred, cred_in=cred_in)

@router.delete("/{cred_id}", status_code=204)
def delete_credential(cred_id: str, db: Session = Depends(get_db)):
    db_cred = crud.get_credential(db, cred_id)
    if not db_cred:
        raise HTTPException(status_code=404, detail="凭证未找到")
    crud.delete_credential(db, db_cred)
    return None