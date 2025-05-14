"""crear_tablas_iniciales

Revision ID: 42ffb5e7d983
Revises:
Create Date: 2025-04-23 17:00:05.337704

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "42ffb5e7d983"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First create tables with no dependencies
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("cuit", sa.String(20), nullable=False),
        sa.Column("client_folder", sa.String(255), nullable=False),
        sa.Column("correo_output", sa.String(255), nullable=True),
        sa.Column("socio_responsable", sa.String(255), nullable=True),
        sa.Column("zip_password", sa.String(255), nullable=True),
        sa.Column("rango_consulta_dias", sa.Integer(), nullable=True, default=7),
        sa.Column("dias_ejecucion", sa.String(255), nullable=True),
        sa.Column("documentacion", sa.Boolean(), nullable=True, default=True),
        sa.Column("filtro_fce", sa.Boolean(), nullable=True, default=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clientes_id"), "clientes", ["id"], unique=False)

    op.create_table(
        "jurisdicciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("clase", sa.String(255), nullable=False),
        sa.Column("headless", sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_jurisdicciones_id"), "jurisdicciones", ["id"], unique=False
    )

    op.create_table(
        "usuarios_autorizados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("fecha_autorizacion", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_usuarios_autorizados_id"), "usuarios_autorizados", ["id"], unique=False
    )

    # Then create procesamientos_diarios_global
    op.create_table(
        "procesamientos_diarios_global",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("numero_procesamiento", sa.Integer(), nullable=False),
        sa.Column("iniciado", sa.DateTime(), nullable=False),
        sa.Column("finalizado", sa.DateTime(), nullable=True),
        sa.Column("procesamiento_correcto", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_procesamientos_diarios_global_id"),
        "procesamientos_diarios_global",
        ["id"],
        unique=False,
    )

    # Then tables with foreign keys
    op.create_table(
        "monitoreo_bots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(50), nullable=False),
        sa.Column("iniciado", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalizado", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("id_procesamiento_diario_global", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["id_procesamiento_diario_global"],
            ["procesamientos_diarios_global.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_monitoreo_bots_id"), "monitoreo_bots", ["id"], unique=False
    )

    # Finally other relationship tables
    op.create_table(
        "cliente_jurisdiccion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("jurisdiccion_id", sa.Integer(), nullable=True),
        sa.Column("usuario", sa.String(255), nullable=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("consultar", sa.Boolean(), nullable=True, default=True),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.Column("fecha_login_error", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiccion_id"],
            ["jurisdicciones.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cliente_jurisdiccion_id"), "cliente_jurisdiccion", ["id"], unique=False
    )

    op.create_table(
        "usuario_cliente",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=True),
        sa.Column("id_cliente", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_cliente"],
            ["clientes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["usuarios_autorizados.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_usuario_cliente_id"), "usuario_cliente", ["id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_usuario_cliente_id"), table_name="usuario_cliente")
    op.drop_table("usuario_cliente")
    op.drop_index(op.f("ix_cliente_jurisdiccion_id"), table_name="cliente_jurisdiccion")
    op.drop_table("cliente_jurisdiccion")
    op.drop_index(op.f("ix_monitoreo_bots_id"), table_name="monitoreo_bots")
    op.drop_table("monitoreo_bots")
    op.drop_index(
        op.f("ix_procesamientos_diarios_global_id"),
        table_name="procesamientos_diarios_global",
    )
    op.drop_table("procesamientos_diarios_global")
    op.drop_index(op.f("ix_usuarios_autorizados_id"), table_name="usuarios_autorizados")
    op.drop_table("usuarios_autorizados")
    op.drop_index(op.f("ix_jurisdicciones_id"), table_name="jurisdicciones")
    op.drop_table("jurisdicciones")
    op.drop_index(op.f("ix_clientes_id"), table_name="clientes")
    op.drop_table("clientes")
    # ### end Alembic commands ###
