from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


# ---------------------------------------------------------------------------
# Monedas y TRM
# ---------------------------------------------------------------------------

class AdmMoneda(Base, AuditMixin):
    __tablename__ = "adm_moneda"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    simbolo: Mapped[str] = mapped_column(String(10), nullable=False)
    decimales: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    es_funcional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    trm_origen: Mapped[list["AdmTrm"]] = relationship("AdmTrm", foreign_keys="AdmTrm.moneda_origen_id", back_populates="moneda_origen")
    trm_destino: Mapped[list["AdmTrm"]] = relationship("AdmTrm", foreign_keys="AdmTrm.moneda_destino_id", back_populates="moneda_destino")


class AdmTrm(Base):
    __tablename__ = "adm_trm"
    __table_args__ = (
        UniqueConstraint("moneda_origen_id", "moneda_destino_id", "fecha", name="uq_trm_moneda_fecha"),
        CheckConstraint("moneda_origen_id <> moneda_destino_id", name="chk_monedas_distintas"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    moneda_origen_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=False)
    moneda_destino_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    tasa: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    fuente: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)

    moneda_origen: Mapped["AdmMoneda"] = relationship("AdmMoneda", foreign_keys=[moneda_origen_id], back_populates="trm_origen")
    moneda_destino: Mapped["AdmMoneda"] = relationship("AdmMoneda", foreign_keys=[moneda_destino_id], back_populates="trm_destino")


# ---------------------------------------------------------------------------
# Empresa y configuración
# ---------------------------------------------------------------------------

class AdmEmpresa(Base, AuditMixin):
    __tablename__ = "adm_empresa"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    digito_verif: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ciudad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    departamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    regimen: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    responsable_iva: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    moneda_funcional_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_moneda.id"), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actividad_economica_codigo: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    actividad_economica_descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    moneda_funcional: Mapped[Optional["AdmMoneda"]] = relationship("AdmMoneda")


class AdmConfiguracion(Base):
    __tablename__ = "adm_configuracion"

    clave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False,
        info={"check": "tipo IN ('string','boolean','integer','numeric')"}
    )
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modificado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    modificado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)


# ---------------------------------------------------------------------------
# Roles, módulos y permisos
# ---------------------------------------------------------------------------

class AdmModulo(Base):
    __tablename__ = "adm_modulo"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)



class AdmRol(Base):
    __tablename__ = "adm_rol"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    es_cliente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)

    usuarios: Mapped[list["AdmUsuario"]] = relationship("AdmUsuario", back_populates="rol")


class AdmUsuario(Base, AuditMixin):
    __tablename__ = "adm_usuario"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_rol.id"), nullable=False)
    tercero_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tercero.id"), nullable=True)
    es_asesor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ver_solo_propios: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ultimo_acceso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    rol: Mapped["AdmRol"] = relationship("AdmRol", back_populates="usuarios")
    tercero: Mapped[Optional["AdmTercero"]] = relationship("AdmTercero", foreign_keys=[tercero_id])
    sesiones: Mapped[list["AdmSesion"]] = relationship("AdmSesion", back_populates="usuario")
    resets: Mapped[list["AdmPasswordReset"]] = relationship("AdmPasswordReset", back_populates="usuario")


# ---------------------------------------------------------------------------
# Sesiones y recuperación de contraseña
# ---------------------------------------------------------------------------

class AdmSesion(Base):
    __tablename__ = "adm_sesion"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    usuario: Mapped["AdmUsuario"] = relationship("AdmUsuario", back_populates="sesiones")


class AdmPasswordReset(Base):
    __tablename__ = "adm_password_reset"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_usuario.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    usuario: Mapped["AdmUsuario"] = relationship("AdmUsuario", back_populates="resets")


# ---------------------------------------------------------------------------
# Tipos de documento y consecutivos
# ---------------------------------------------------------------------------

class AdmTipoDocumento(Base):
    __tablename__ = "adm_tipo_documento"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    consecutivo: Mapped[Optional["AdmConsecutivo"]] = relationship("AdmConsecutivo", back_populates="tipo_documento", uselist=False)


class AdmConsecutivo(Base):
    __tablename__ = "adm_consecutivo"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_tipo_documento.id"), unique=True, nullable=False)
    prefijo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    numero_actual: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    numero_inicio: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    longitud_minima: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    modificado_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    modificado_por: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), nullable=True)

    tipo_documento: Mapped["AdmTipoDocumento"] = relationship("AdmTipoDocumento", back_populates="consecutivo")


# ---------------------------------------------------------------------------
# Auditoría centralizada
# ---------------------------------------------------------------------------

class AdmAuditoria(Base):
    __tablename__ = "adm_auditoria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tabla: Mapped[str] = mapped_column(String(100), nullable=False)
    registro_id: Mapped[str] = mapped_column(String(100), nullable=False)
    accion: Mapped[str] = mapped_column(
        String(10), nullable=False,
        info={"check": "accion IN ('INSERT','UPDATE','DELETE')"}
    )
    campo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    valor_anterior: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_nuevo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    contexto: Mapped[Optional[dict]] = mapped_column(pg.JSONB, nullable=True)


# ---------------------------------------------------------------------------
# Conceptos contables
# ---------------------------------------------------------------------------

class AdmConcepto(Base, AuditMixin):
    __tablename__ = "adm_concepto"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tarifa_iva_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_tarifa_iva.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cuenta_gasto_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_cxp_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)

    tarifa_iva: Mapped[Optional["AdmTarifaIva"]] = relationship("AdmTarifaIva", foreign_keys=[tarifa_iva_id])
    cuenta_gasto: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_gasto_id])
    cuenta_cxp: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_cxp_id])
    retenciones: Mapped[list["AdmConceptoRetencion"]] = relationship("AdmConceptoRetencion", back_populates="concepto", cascade="all, delete-orphan")


class AdmConceptoRetencion(Base):
    __tablename__ = "adm_concepto_retencion"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concepto_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_concepto.id"), nullable=False)
    retencion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_retencion.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    concepto: Mapped["AdmConcepto"] = relationship("AdmConcepto", back_populates="retenciones")
    retencion: Mapped["AdmRetencion"] = relationship("AdmRetencion", foreign_keys=[retencion_id])



# ---------------------------------------------------------------------------
# Opciones de menú y permisos por opción
# ---------------------------------------------------------------------------

class AdmOpcion(Base):
    __tablename__ = "adm_opcion"
    __table_args__ = (
        UniqueConstraint("modulo_id", "codigo", name="uq_opcion_modulo_codigo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modulo_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_modulo.id"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    ruta: Mapped[str] = mapped_column(String(200), nullable=False)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    implementada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    modulo: Mapped["AdmModulo"] = relationship("AdmModulo")
    permisos: Mapped[list["AdmPermisoOpcion"]] = relationship("AdmPermisoOpcion", back_populates="opcion")


class AdmPermisoOpcion(Base):
    __tablename__ = "adm_permiso_opcion"
    __table_args__ = (
        UniqueConstraint("rol_id", "opcion_id", name="uq_permiso_opcion_rol"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rol_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_rol.id"), nullable=False)
    opcion_id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("adm_opcion.id"), nullable=False)
    puede_ver: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    puede_crear: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    puede_editar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    puede_eliminar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    puede_imprimir: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    puede_autorizar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rol: Mapped["AdmRol"] = relationship("AdmRol")
    opcion: Mapped["AdmOpcion"] = relationship("AdmOpcion", back_populates="permisos")


# ---------------------------------------------------------------------------
# Condiciones de pago
# ---------------------------------------------------------------------------

class AdmCondicionPago(Base, AuditMixin):
    __tablename__ = "adm_condicion_pago"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    dias_vencimiento: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    descuento_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ---------------------------------------------------------------------------
# Tarifas de IVA
# ---------------------------------------------------------------------------

class AdmTarifaIva(Base, AuditMixin):
    __tablename__ = "cnt_tarifa_iva"
    __table_args__ = (
        CheckConstraint("tipo IN ('GRAVADO','EXENTO','EXCLUIDO')", name="chk_tarifa_iva_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    cuenta_iva_ventas_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_iva_compras_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cuenta_iva_ventas: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_iva_ventas_id])
    cuenta_iva_compras: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_iva_compras_id])


# ---------------------------------------------------------------------------
# Retenciones
# ---------------------------------------------------------------------------

class AdmRetencion(Base, AuditMixin):
    __tablename__ = "cnt_retencion"
    __table_args__ = (
        CheckConstraint("tipo IN ('RETEFUENTE','RETEICA','RETEIVA')", name="chk_retencion_tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    base_minima: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    cuenta_compras_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    cuenta_ventas_id: Mapped[Optional[uuid.UUID]] = mapped_column(pg.UUID(as_uuid=True), ForeignKey("cnt_cuenta.id"), nullable=True)
    aplica_compra: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aplica_venta: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    cuenta_compras: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_compras_id])
    cuenta_ventas: Mapped[Optional["CntCuenta"]] = relationship("CntCuenta", foreign_keys=[cuenta_ventas_id])
