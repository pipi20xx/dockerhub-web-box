from pydantic import BaseModel, Field

class CredentialBase(BaseModel):
    name: str
    username: str

class CredentialCreate(CredentialBase):
    password: str

class CredentialUpdate(BaseModel):
    name: str | None = None
    username: str | None = None
    password: str | None = None

class Credential(CredentialBase):
    id: str
    password: str | None = None

    class Config:
        from_attributes = True