from fastapi import FastAPI, Depends, Query, HTTPException
from typing import List
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Book
from schemas import BookSchema, BookCreateSchema
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate

app = FastAPI()
add_pagination(app)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def home():
    return {"message": "Hello World"}

@app.post("/books/", response_model=BookSchema)
async def add_book(request: BookCreateSchema, db: Session = Depends(get_db)):
    new_book = Book(title = request.title, author = request.author, published_date = request.published_date, summary = request.summary, genre = request.genre)
    db.add(new_book)
    db.commit()
    return new_book


@app.get("/books/", response_model=Page[BookSchema])
async def get_books(id: int = Query(None, description="Filter by book ID"), db: Session = Depends(get_db)):
    if id:
        book = db.query(Book).filter(Book.id == id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        book_schema = BookSchema.from_orm(book)
        return Page[BookSchema](items=[book_schema], total=1, page=1, size=1)
    else:
        return paginate(db.query(Book))
    

@app.put("/books/{id}", response_model=BookSchema)
async def update_book(id: int, request: BookCreateSchema, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book.title = request.title
    book.author = request.author
    book.published_date = request.published_date
    book.summary = request.summary
    book.genre = request.genre
    db.commit()
    return book


@app.delete("/books/{id}")
async def delete_book(id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}





