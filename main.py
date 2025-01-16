from fastapi import FastAPI, Depends, Query, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Book
from schemas import BookSchema, BookCreateSchema, UserSchema
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate
from auth import create_access_token, oauth2_scheme, SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
import asyncio
import logging

# app = FastAPI()
app = FastAPI(
    title="Bookstore API",
    description="API for managing books",
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication endpoints. Use `/token` to get an access token."
        },
        {
            "name": "books",
            "description": "Operations with books. The `/books` endpoints require authentication."
        }
    ],
    swagger_ui_parameters={"persistAuthorization": True}
)
add_pagination(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users = {}
event_queue = asyncio.Queue()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def home():
    return {"message": "Welcome to the Book API!"}

# user auth for protected routes
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        logger.info(f"Decoded username from token: {username}")
        if not username:
            logger.warning(f"Authentication failed for user: {username}")
            raise HTTPException(status_code=401, detail="Invalid token or user does not exist")
        return username
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"An error occurred: {exc} for request: {request}", exc_info=True)    
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

@app.post("/register", summary="Register a new user", description="Register a new user", tags=["auth"])
async def register(user: UserSchema):
    if user.username in users:
        raise HTTPException(status_code=400, detail="Username already registered")
    users[user.username] = user.password  # storing plain text password (for testing only)
    return {"msg": "User registered successfully"}

@app.post("/token", summary="Get access token (please register and authorize above first)", description="Login/get access token", tags=["auth"])
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

@app.post("/books/", response_model=BookSchema, summary="Add a new book", description="Add a new book to the database", tags=["books"])
async def add_book(request: BookCreateSchema, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    new_book = Book(title = request.title, author = request.author, published_date = request.published_date, summary = request.summary, genre = request.genre)
    db.add(new_book)
    db.commit()
    await event_queue.put(f"New book added: {new_book.title}")
    return new_book

@app.get("/books/", response_model=Page[BookSchema], summary="Get all books or a specific book", description="Get all books from the database or a specific book by ID", tags=["books"])
async def get_books(id: int = Query(None, description="Filter by book ID"), page: int = Query(1, ge=1, description="Page number"), size: int = Query(10, ge=1, le=100, description="Page size"), db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    if id:
        book = db.query(Book).filter(Book.id == id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        book_schema = BookSchema.from_orm(book)
        await event_queue.put(f"Book found: {book_schema.title}")
        return Page[BookSchema](items=[book_schema], total=1, page=1, size=1)
    else:
        return paginate(db.query(Book))
    

@app.put("/books/{id}", response_model=BookSchema, summary="Update a book", description="Update a book in the database", tags=["books"])
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
    await event_queue.put(f"Book updated: {book.title}")
    return book

@app.delete("/books/{id}", summary="Delete a book", description="Delete a book from the database", tags=["books"])
async def delete_book(id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    await event_queue.put(f"Book deleted: {book.title}")
    return {"message": "Book deleted successfully"}

@app.get("/events", summary="Get server sent events (SSE's)", description="Get server sent events --> use curl -N \<url\> -H ""Authorization: Bearer \<token\>"" to test", tags=["events"])
async def sse_get_events(current_user: str = Depends(get_current_user)):
    async def event_generator():
        while True:
            event = await event_queue.get()
            yield f"{event}"
    return EventSourceResponse(content=event_generator(), media_type="text/event-stream")






