from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator, model_validator



class PermissionOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    permissions: list[PermissionOut] = []

    model_config = {"from_attributes": True}



class UserRegister(BaseModel):
    first_name: str
    last_name: str
    middle_name: str | None = None
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "UserRegister":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    password_confirm: str | None = None

    @model_validator(mode="after")
    def passwords_match(self) -> "UserUpdate":
        if self.password or self.password_confirm:
            if self.password != self.password_confirm:
                raise ValueError("Passwords do not match")
        return self


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    middle_name: str | None = None
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    roles: list[RoleOut] = []

    model_config = {"from_attributes": True}
