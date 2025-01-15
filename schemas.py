from pydantic import BaseModel
import datetime

class BookCreateSchema(BaseModel):
    title: str
    author: str
    published_date: datetime.date
    summary: str
    genre: str


class BookSchema(BaseModel):
    id: int
    title: str
    author: str
    published_date: datetime.date
    summary: str
    genre: str
