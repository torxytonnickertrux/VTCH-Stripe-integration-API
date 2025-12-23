from pydantic import BaseModel, Field, ValidationError

from typing import Optional

from typing import Optional

class CreateProductSchema(BaseModel):
    productName: str = Field(min_length=1)
    productDescription: str = Field(min_length=1)
    productPrice: int = Field(gt=0)
    accountId: str = Field(min_length=1)
    recurringInterval: Optional[str] = None  # None for one-time, "month"/"year" for subscription

class CreateCheckoutSessionSchema(BaseModel):
    accountId: str = Field(min_length=1)
    priceId: str = Field(min_length=1)
    successUrl: Optional[str] = None
    cancelUrl: Optional[str] = None
    orderId: Optional[str] = None

class SubscribePlatformSchema(BaseModel):
    accountId: str = Field(min_length=1)
    successUrl: Optional[str] = None
    cancelUrl: Optional[str] = None

class CreatePortalSessionSchema(BaseModel):
    session_id: str = Field(min_length=1)

def parse_and_validate(schema, data):
    try:
        return schema(**data), None
    except ValidationError as e:
        return None, {"error": "invalid_payload", "details": e.errors()}
