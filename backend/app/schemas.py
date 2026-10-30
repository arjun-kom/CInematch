from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.]+$")
    password: str = Field(min_length=6, max_length=100)
    display_name: str | None = Field(default=None, max_length=50)


class Login(BaseModel):
    username: str
    password: str


class Onboarding(BaseModel):
    genres: list[str] = Field(min_length=1, max_length=10)
    movie_ids: list[str] = Field(default_factory=list, max_length=50)


class Preferences(BaseModel):
    favourite_genres: list[str] = Field(min_length=1, max_length=10)


class ListItem(BaseModel):
    movie_id: str


class RatingIn(BaseModel):
    stars: int = Field(ge=1, le=5)
