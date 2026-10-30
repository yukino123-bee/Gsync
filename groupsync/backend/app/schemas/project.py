from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.common import ORMModel, UserBrief, UtcDatetime


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    rubric: str = Field(default="", max_length=10000)
    deadline: UtcDatetime | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    rubric: str | None = Field(default=None, max_length=10000)
    deadline: UtcDatetime | None = None


class ProjectOut(ORMModel):
    id: int
    teacher_id: int
    title: str
    description: str
    rubric: str
    deadline: UtcDatetime | None
    created_at: UtcDatetime
    group_count: int = 0


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    member_ids: list[int] = Field(default_factory=list, max_length=50)


class MemberAdd(BaseModel):
    user_id: int | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def one_of(self):
        if (self.user_id is None) == (self.email is None):
            raise ValueError("Provide exactly one of user_id or email")
        return self


class RandomizeRequest(BaseModel):
    group_size: int = Field(ge=1, le=20)
    # Defaults to every student not yet in a group of this project
    student_ids: list[int] | None = None


class GroupOut(BaseModel):
    id: int
    project_id: int | None
    name: str
    group_code: str
    status: str
    join_enabled: bool
    created_by: int | None
    created_at: UtcDatetime
    members: list[UserBrief]
    # The teacher who added this group with its Group ID, if any
    teacher: UserBrief | None = None
    project: ProjectOut | None
