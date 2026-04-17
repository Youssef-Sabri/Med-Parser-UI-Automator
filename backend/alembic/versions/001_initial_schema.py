"""Initial clinical schema."""

import sqlalchemy as sa
from alembic import op

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'extractions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('image_hash', sa.String(), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('data_json', sa.Text(), nullable=True),
        sa.Column('flags_json', sa.Text(), nullable=True),
        sa.Column('prompt_version', sa.String(), nullable=True),
        sa.Column('is_encrypted', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_extractions_id'), 'extractions', ['id'], unique=False)
    op.create_index(op.f('ix_extractions_image_hash'), 'extractions', ['image_hash'], unique=True)
    op.create_index(op.f('ix_extractions_status'), 'extractions', ['status'])
    op.create_index(op.f('ix_extractions_created_at'), 'extractions', ['created_at'])

    op.create_table(
        'pharmacist_actions',
        sa.Column('action_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('extraction_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('pharmacist_note', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['extraction_id'], ['extractions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('action_id'),
    )
    op.create_index(op.f('ix_pharmacist_actions_action_id'), 'pharmacist_actions', ['action_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pharmacist_actions_action_id'), table_name='pharmacist_actions')
    op.drop_table('pharmacist_actions')
    op.drop_index(op.f('ix_extractions_created_at'), table_name='extractions')
    op.drop_index(op.f('ix_extractions_status'), table_name='extractions')
    op.drop_index(op.f('ix_extractions_image_hash'), table_name='extractions')
    op.drop_index(op.f('ix_extractions_id'), table_name='extractions')
    op.drop_table('extractions')
