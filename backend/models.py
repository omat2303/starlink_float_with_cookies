"""SQLAlchemy ORM models for the StarPanel fleet panel."""
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    region_code: Mapped[str | None] = mapped_column(String(10))
    currency_code: Mapped[str | None] = mapped_column(String(10))
    is_billing_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    next_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    balance_due: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    antennas: Mapped[list["Antenna"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class Antenna(Base):
    __tablename__ = "antennas"

    id: Mapped[int] = mapped_column(primary_key=True)
    kit_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False, index=True
    )
    service_line_number: Mapped[str | None] = mapped_column(String(50))
    nickname: Mapped[str | None] = mapped_column(String(200))  # apodo que trae Starlink
    custom_name: Mapped[str | None] = mapped_column(String(200))  # nombre propio (paralelo a Starlink)
    model: Mapped[str] = mapped_column(String(50), default="Desconocido", nullable=False)
    plan: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_standby: Mapped[bool | None] = mapped_column(Boolean, default=None)
    subscription_status: Mapped[int | None] = mapped_column(Integer, default=None)
    activation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cycles_json: Mapped[str | None] = mapped_column(String)  # historial de ciclos de consumo (JSON)
    data_cycle_gb: Mapped[float | None] = mapped_column(Float)
    data_limit_gb: Mapped[float | None] = mapped_column(Float)
    data_total_gb: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    last_connected: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped["Account"] = relationship(back_populates="antennas")


class ClientAlias(Base):
    """Reasigna una cuenta a otro cliente (cuenta a nombre propio que es de un cliente)."""

    __tablename__ = "client_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)


class Gestion(Base):
    """Datos de gestión por cliente: si lo administramos, quién paga, costo y precio.

    Vive aparte de ``accounts`` para que el sync del portal nunca lo pise.
    """

    __tablename__ = "gestiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    is_administered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_paid_by_us: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cost: Mapped[float | None] = mapped_column(Float)   # lo que pagamos por el cliente/mes
    price: Mapped[float | None] = mapped_column(Float)  # lo que le cobramos/mes
    currency: Mapped[str | None] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(String(500))


class SyncState(Base):
    """Última sincronización, para la barra de estado del panel."""

    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accounts: Mapped[int] = mapped_column(default=0, nullable=False)
    antennas: Mapped[int] = mapped_column(default=0, nullable=False)
