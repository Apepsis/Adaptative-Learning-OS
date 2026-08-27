from sqlalchemy.orm import DeclarativeBase

# Consistent constraint naming so Alembic autogenerate produces stable,
# diffable migrations instead of driver-assigned names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata_naming_convention = NAMING_CONVENTION
    # eager_defaults defaults to "auto" in SQLAlchemy 2.0, which only uses
    # RETURNING to populate server-side defaults (e.g. onupdate=func.now())
    # on INSERT, not UPDATE. Any model updated and then re-serialized in
    # the same request (e.g. StudyGuide regeneration, NotebookNote edits)
    # would otherwise need a lazy-load for that column, which fails under
    # async SQLAlchemy (MissingGreenlet) outside an explicit await. Forcing
    # it on covers UPDATE too — verified directly against real Postgres.
    __mapper_args__ = {"eager_defaults": True}


Base.metadata.naming_convention = NAMING_CONVENTION
