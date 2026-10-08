"""initial_platform_schema

Revision ID: b8beb982cb32
Revises: 
Create Date: 2026-10-08 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b8beb982cb32'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Tabela de Produtos (Vendas / Recomendação)
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)

    # 2. Tabela de Tickets de Suporte e Trocas (Assistente Técnico)
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_number', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('issue_description', sa.Text(), nullable=False),
        sa.Column('solution_guide', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_support_tickets_id'), 'support_tickets', ['id'], unique=False)
    op.create_index(op.f('ix_support_tickets_ticket_number'), 'support_tickets', ['ticket_number'], unique=True)
    op.create_index(op.f('ix_support_tickets_category'), 'support_tickets', ['category'], unique=False)

    # 3. Tabela Global de Resultados de Tarefas
    op.create_table(
        'task_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('agent_response', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_results_id'), 'task_results', ['id'], unique=False)
    op.create_index(op.f('ix_task_results_task_id'), 'task_results', ['task_id'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_task_results_task_id'), table_name='task_results')
    op.drop_index(op.f('ix_task_results_id'), table_name='task_results')
    op.drop_table('task_results')
    op.drop_index(op.f('ix_support_tickets_category'), table_name='support_tickets')
    op.drop_index(op.f('ix_support_tickets_ticket_number'), table_name='support_tickets')
    op.drop_index(op.f('ix_support_tickets_id'), table_name='support_tickets')
    op.drop_table('support_tickets')
    op.drop_index(op.f('ix_products_name'), table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')
