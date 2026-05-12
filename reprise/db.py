import os
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import backref, declarative_base, relationship, sessionmaker
from sqlalchemy.schema import ForeignKey

database = os.getenv("DATABASE_URL", "sqlite:///reprise.db")
engine = create_engine(database, echo=False)

Base = declarative_base()

SessionLocal = sessionmaker(bind=engine)


@contextmanager
def database_session():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.commit()
        session.close()


class Motif(Base):
    __tablename__ = "motif"

    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    citation_uuid = Column(String(36), ForeignKey("citation.uuid"), nullable=True)

    citation = relationship("Citation", backref="motifs")
    cloze_deletions = relationship(
        "ClozeDeletion", back_populates="motif", cascade="all, delete-orphan"
    )


class Citation(Base):
    __tablename__ = "citation"

    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class Reprisal(Base):
    __tablename__ = "reprisal"

    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    motif_uuid = Column(String(36), ForeignKey("motif.uuid"), nullable=False)
    set_uuid = Column(String(36), nullable=False)
    cloze_deletion_uuid = Column(
        String(36), ForeignKey("cloze_deletion.uuid"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    motif = relationship(
        "Motif", backref=backref("reprisals", cascade="all, delete-orphan")
    )
    cloze_deletion = relationship("ClozeDeletion", backref="reprisals")


class ClozeDeletion(Base):
    __tablename__ = "cloze_deletion"

    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    motif_uuid = Column(String(36), ForeignKey("motif.uuid"), nullable=False)
    mask_tuples = Column(JSON, nullable=False)  # stores a list of (start, end) tuples
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    motif = relationship("Motif", back_populates="cloze_deletions")

    def masked_motif(self, mask: str = "*") -> str:
        motif_content = self.motif.content
        n_removed_characters = 0
        for start, end in self.mask_tuples:
            start -= n_removed_characters
            end -= n_removed_characters

            motif_content = motif_content[:start] + mask + motif_content[end + 1 :]
            n_removed_characters += end - start + 1 - len(mask)
        return motif_content

    def masked_words(self) -> list[str]:
        return [self.motif.content[start : end + 1] for start, end in self.mask_tuples]


class ReprisalSchedule(Base):
    __tablename__ = "reprisal_schedule"

    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reprisal_set_uuid = Column(String(36), nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
