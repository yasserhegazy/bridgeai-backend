from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Comment(Base):
    __tablename__ = "comments"


    id = Column(Integer, primary_key=True, index=True)
    crs_id = Column(Integer, ForeignKey("crs_documents.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    crs_document = relationship("CRSDocument", backref="comments")
    author = relationship("User", backref="comments")