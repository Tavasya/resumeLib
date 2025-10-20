"""
Pydantic models for Resume data
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class Experience(BaseModel):
    """Single work experience entry"""
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class Education(BaseModel):
    """Single education entry"""
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_date: Optional[str] = None


class Project(BaseModel):
    """Single project entry"""
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = None
    url: Optional[str] = None


class Certification(BaseModel):
    """Single certification entry"""
    name: Optional[str] = None
    issuer: Optional[str] = None
    date: Optional[str] = None


class ResumeCreate(BaseModel):
    """Schema for creating a new resume"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    seniority: Optional[str] = None
    years_of_experience: Optional[int] = None
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    search_query: Optional[str] = None
    source_url: Optional[str] = None
    raw_text: Optional[str] = None


class ResumeInDB(ResumeCreate):
    """Schema for resume stored in database"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeUpdate(BaseModel):
    """Schema for updating a resume"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    seniority: Optional[str] = None
    years_of_experience: Optional[int] = None
    experience: Optional[List[Experience]] = None
    education: Optional[List[Education]] = None
    projects: Optional[List[Project]] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[Certification]] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    search_query: Optional[str] = None
    source_url: Optional[str] = None
    raw_text: Optional[str] = None
