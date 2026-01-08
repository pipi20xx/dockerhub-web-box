from pydantic import BaseModel
from typing import Optional

class RegistryBase(BaseModel):
    name: str
    url: str
    is_https: bool = True
    credential_id: Optional[str] = None

class RegistryCreate(RegistryBase):
    pass

class Registry(RegistryBase):
    id: str

    class Config:
        from_attributes = True
