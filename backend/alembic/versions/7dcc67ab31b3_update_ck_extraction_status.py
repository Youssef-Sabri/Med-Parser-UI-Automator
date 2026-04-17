"""update ck_extraction_status

Revision ID: 7dcc67ab31b3
Revises: 001_initial_schema
Create Date: 2026-04-09 04:21:44.127412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7dcc67ab31b3'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE extractions DROP CONSTRAINT IF EXISTS ck_extraction_status")
    op.execute(
        "ALTER TABLE extractions ADD CONSTRAINT ck_extraction_status "
        "CHECK (status IN ('PENDING', 'QUEUED', 'PROCESSING', 'PROCESSED', 'FAILED', 'INJECTING', 'INJECTED'))"
    )

def downgrade() -> None:
    op.execute("ALTER TABLE extractions DROP CONSTRAINT IF EXISTS ck_extraction_status")
    op.execute(
        "ALTER TABLE extractions ADD CONSTRAINT ck_extraction_status "
        "CHECK (status IN ('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED'))"
    )
