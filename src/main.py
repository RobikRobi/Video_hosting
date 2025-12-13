from binascii import Error
from fastapi import FastAPI
from src.db import engine,Base


from src.models.UserModel import User
from src.auth.auth_router import app as auth_router



app = FastAPI()

# routers
app.include_router(auth_router)


@app.get("/init")
async def create_db():
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Error as e:
            print(e)     
        await  conn.run_sync(Base.metadata.create_all)
    return({"msg":"db creat! =)"})