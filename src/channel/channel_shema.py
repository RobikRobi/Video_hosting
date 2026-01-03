from pydantic import BaseModel, Field



class CreateChannel(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    img: str | None = None