from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Insight(BaseModel):
    post_id: str
    created_at: datetime
    first_view: str
    followers_reach_count: int
    like_count: int
    new_reach_count: int
    plot: Optional[str] = None
    reach_count: str  # 文字列として保存されているため
    save_count: int

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_dict(cls, data: dict):
        if 'created_at' in data and isinstance(data['created_at'], (int, float)):
            data['created_at'] = datetime.fromtimestamp(data['created_at'])
        return cls(**data)
