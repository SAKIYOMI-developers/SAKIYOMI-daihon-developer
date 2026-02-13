# domain/billing.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime


class Billing(BaseModel):
    billing_id: str = Field(..., min_length=1, max_length=100)
    user_id: str = Field(..., min_length=1, max_length=100)
    plan: str = Field(..., min_length=1, max_length=50)
    payment_date: Optional[datetime] = None
    cancellation_date: Optional[datetime] = None
    status: str = Field(..., min_length=1, max_length=20)

    @field_validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'cancelled', 'pending']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of {allowed_statuses}')
        return v

    @field_validator('payment_date', 'cancellation_date', mode='before')
    def validate_dates(cls, v):
        if v is not None and not isinstance(v, datetime):
            raise ValueError('Date fields must be a datetime object')
        return v

    @model_validator(mode='after')
    def check_dates(cls, billing):
        if billing.cancellation_date and billing.payment_date:
            if billing.cancellation_date < billing.payment_date:
                raise ValueError('Cancellation date cannot be before payment date')
        return billing

    class Config:
        arbitrary_types_allowed = True
        anystr_strip_whitespace = True
        min_anystr_length = 1
        max_anystr_length = 1000
        use_enum_values = True
        validate_assignment = True
