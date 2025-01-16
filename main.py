from fastapi import FastAPI, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Book
from schemas import BookSchema, BookCreateSchema, UserSchema
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate
from auth import create_access_token, oauth2_scheme, SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt

app = FastAPI()
add_pagination(app)

users = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def home():
    return {"message": "Hello World"}

# user auth for protected routes
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username or username not in users: # check if user exists
            raise HTTPException(status_code=401, detail="Invalid token or user does not exist")
        return username 
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/register")
async def register(user: UserSchema):
    if user.username in users:
        raise HTTPException(status_code=400, detail="Username already registered")
    users[user.username] = user.password  # storing plain text password (for testing only)
    return {"msg": "User registered successfully"}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_password = users.get(form_data.username)
    if not user_password or form_data.password != user_password:  # simple password check
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/books/", response_model=BookSchema)
async def add_book(request: BookCreateSchema, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    new_book = Book(title = request.title, author = request.author, published_date = request.published_date, summary = request.summary, genre = request.genre)
    db.add(new_book)
    db.commit()
    return new_book


@app.get("/books/", response_model=Page[BookSchema])
async def get_books(id: int = Query(None, description="Filter by book ID"), db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    if id:
        book = db.query(Book).filter(Book.id == id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        book_schema = BookSchema.from_orm(book)
        return Page[BookSchema](items=[book_schema], total=1, page=1, size=1)
    else:
        return paginate(db.query(Book))
    

@app.put("/books/{id}", response_model=BookSchema)
async def update_book(id: int, request: BookCreateSchema, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
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
async def delete_book(id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}





