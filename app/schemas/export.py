from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    markdown = "markdown"
    pdf = "pdf"
    csv = "csv"


class ExportRequest(BaseModel):
    filename: Optional[str] = Field(
        None, description="Desired filename including extension"
    )
    format: ExportFormat = Field(..., description="Export format: markdown or pdf")
    content: Optional[str] = Field(None, description="Content to export")
    requirements_only: bool = Field(
        False, description="If true, export only requirements (CSV only)"
    )
