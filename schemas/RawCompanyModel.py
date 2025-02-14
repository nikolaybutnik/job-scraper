from typing import Optional
from pydantic import BaseModel


class Address(BaseModel):
    street: str
    city: str
    province: str
    country: str


class RawCompanyModel(BaseModel):
    name: str
    address: Address
    website: str


schema = RawCompanyModel.model_json_schema()
