from binascii import Error
from fastapi import FastAPI
from src.db import engine,Base


from src.models.UserModel import User
from src.authors.router import app as authors_app
from src.books.router import app as books_app



app = FastAPI()

# routers
app.include_router(authors_app)
app.include_router(books_app)

@app.get("/init")
async def create_db():
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Error as e:
            print(e)     
        await  conn.run_sync(Base.metadata.create_all)
    return({"msg":"db creat! =)"})