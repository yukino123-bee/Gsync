from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

from app.services.timeutil import as_utc

# Normalizes both incoming and outgoing datetimes to aware UTC (serialized with a Z suffix)
UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBrief(ORMModel):
    id: int
    name: str
    email: str
