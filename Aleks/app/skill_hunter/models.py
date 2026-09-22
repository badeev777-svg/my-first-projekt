from pydantic import BaseModel


class SkillCandidate(BaseModel):
    title: str
    url: str
    description: str
