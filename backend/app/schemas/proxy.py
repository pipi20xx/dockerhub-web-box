from pydantic import BaseModel

class ProxyBase(BaseModel):
    name: str
    url: str

class ProxyCreate(ProxyBase):
    pass

class ProxyUpdate(BaseModel):
    name: str | None = None
    url: str | None = None

class Proxy(ProxyBase):
    id: str

    class Config:
         from_attributes = True