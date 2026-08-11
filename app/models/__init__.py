from app.models.admin import (
    AdmMoneda,
    AdmTrm,
    AdmEmpresa,
    AdmConfiguracion,
    AdmModulo,
    AdmRol,
    AdmUsuario,
    AdmSesion,
    AdmPasswordReset,
    AdmTipoDocumento,
    AdmConsecutivo,
    AdmAuditoria,
    AdmConcepto,
    AdmConceptoRetencion,
    AdmCondicionPago,
    AdmTarifaIva,
    AdmRetencion,
)
from app.models.contabilidad import (
    CntPeriodo,
    CntPeriodoReapertura,
    CntCuenta,
    CntCentroCosto,
)
from app.models.adm import AdmTercero
from app.models.adjuntos import AdmAdjunto
from app.models.bancos import BanBanco, BanCuenta
from app.models.facturacion import FacResolucion
# cxc y cxp deben importarse aunque nada de aquí los use por nombre: sin ellos
# sus tablas no entran al metadata y Alembic no puede resolver las FK que les
# apuntan (fac_devolucion.cxc_documento_id), lo que rompía --autogenerate.
from app.models.cxc import (
    CxcDocumento,
    CxcRetencion,
    CxcParametroContable,
    CxcAplicacion,
)
from app.models.cxp import (
    CxpDocumento,
    CxpDocumentoLinea,
    CxpLineaRetencion,
    CxpParametroContable,
    CxpAplicacion,
)
from app.models.inventario import InvBodega, InvFamilia, InvUnidadMedida, InvTipoProducto, InvProducto, InvProductoUm, InvProductoBodega, InvMovimiento, InvMovimientoLinea
from app.models.compras import ComOrdenCompra, ComOcLinea, ComRecepcion, ComRecepcionLinea
from app.models.ope import (
    OpeAerolinea,
    OpeAeropuerto,
    OpeConcepto,
    OpeCotizacion,
    OpeCotizacionLinea,
    OpeOperacion,
    OpeHawb,
    OpeMawb,
    OpeManifiesto,
    OpeManifiestoLinea,
    OpeEvento,
    OpeDocumento,
    OpeConfirmacionLinea,
    OpeMbl,
    OpeHbl,
    OpeContenedor,
    OpeHblContenedor,
    OpeBlCargo,
)
from app.models.req import ReqRequerimiento, ReqMensaje
from app.models.nomina import NomPeriodo, NomEmpleado, NomEvento
