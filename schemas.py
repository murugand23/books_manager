from pydantic import BaseModel
import datetime

class Book(BaseModel):
    id: int
    title: str
    author: str
    published_date: datetime.date
    summary: str
    genre: str
