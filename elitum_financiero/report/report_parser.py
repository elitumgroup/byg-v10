# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2016 Ing. Harry Alvarez, Elitum Group                   #
#                                                                       #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                       #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                       #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

from collections import defaultdict
import pytz
from datetime import datetime, timedelta
from odoo import api, fields, models, _


class ReporteRetencionVenta(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_retencion_venta'

    def get_total(self, lines):
        return sum(line.monto for line in lines)

    def get_ano_fiscal(self, fecha):
        fecha_convert = datetime.strptime(fecha, "%Y-%m-%d")
        return fecha_convert.year

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'tax.withhold',
            'docs': self.env['tax.withhold'].browse(docids),
            'data': data,
            'get_ano_fiscal': self.get_ano_fiscal,
            'get_total': self.get_total,
        }
        return self.env['report'].render('elitum_financiero.reporte_retencion_venta', docargs)


class ReporteReposicionCajaChica(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_reposicion_caja_chica'

    def get_periodo(self, lineas):
        fechas = []
        fechas_ordenadas = []
        for line in lineas:
            fechas.append(datetime.strptime(line.date, "%Y-%m-%d"))
        fechas_ordenadas = sorted(fechas)
        periodo = "de " + fechas_ordenadas[0].date().strftime("%Y-%m-%d") + " hasta " + fechas_ordenadas[
            len(fechas_ordenadas) - 1].date().strftime("%Y-%m-%d")
        return periodo

    # MARZ
    def get_lines_factura(self, id):
        factura = self.env['account.invoice'].search([('voucher_caja_chica_id', '=', id)])
        return factura

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'petty.cash.replacement',
            'docs': self.env['petty.cash.replacement'].browse(docids),
            'data': data,
            'get_periodo': self.get_periodo,
            # MARZ
            'get_lines_factura': self.get_lines_factura,
        }
        return self.env['report'].render('elitum_financiero.reporte_reposicion_caja_chica', docargs)


class ReporteComprobanteIngreso(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_comprobante_ingreso'

    def get_total_amount(self, object):
        return sum(line.amount for line in object.lineas_tipos_pagos)

    def get_reference(self, line):
        if line.tipo_de_pagos == 'bank':
            return line.banco.name + " - " + line.numero_cheque
        if line.tipo_de_pagos == 'cash':
            return ""
        if line.tipo_de_pagos == 'transferencia':
            return line.banco.name

    def get_fecha_actual(self):
        return datetime.now(pytz.timezone("America/Guayaquil")).strftime("%Y-%m-%d %H:%M:%S")

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.voucher',
            'docs': self.env['account.voucher'].browse(docids),
            'data': data,
            'get_total_amount': self.get_total_amount,
            'get_reference': self.get_reference,
            'get_fecha_actual': self.get_fecha_actual,
        }
        return self.env['report'].render('elitum_financiero.reporte_comprobante_ingreso', docargs)


# MARZ
class ReportePagoProgramado(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_pago_programado'

    def get_days_mora(self, vencimiento):
        morosidad = 0
        morosidad = (fields.date.today() - vencimiento).days
        return str(morosidad)

    def get_lines(self, doc):
        data = []
        arg = []
        if doc.forma_pago != 'todas':
            arg.append(('way_to_pay', '=', doc.forma_pago))
        pays = self.env['account.invoice.payment.scheduled'].search(arg)
        for pay in pays:
            fecha_pago = pay.fecha
            if (fecha_pago >= doc.fecha_inicio and fecha_pago <= doc.fecha_fin):
                fecha_vencimiento = datetime.strptime(pay.invoice_id.date_due, "%Y-%m-%d").date()
                partner = self.env['res.partner'].browse(pay.invoice_id.partner_id['id'])
                if pay.invoice_id.state == 'open':  # Soló facturas por pagar
                    data.append({
                        'proveedor': partner.name,
                        'number_factura': pay.invoice_id.numero_factura_interno,
                        'subtotal': pay.invoice_id.amount_untaxed,
                        'iva': pay.invoice_id.amount_tax,
                        'total': pay.invoice_id.amount_total,
                        'saldo_pendiente': pay.invoice_id.residual,
                        'fecha_vencimiento': pay.invoice_id.date_due,
                        'morosidad': "SIN MORA" if pay.invoice_id.residual == 0.00 else self.get_days_mora(
                            fecha_vencimiento),
                        'valor_pago': pay.value,
                        'forma_pago': "EFECTIVO" if not pay.bank_id else self.env['res.bank'].browse(
                            pay.bank_id.id).name,
                        'fecha_pago': pay.fecha,
                    })
        return data

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.pagos.programados',
            'docs': self.env['reporte.pagos.programados'].browse(docids),
            'data': data,
            'get_lines': self.get_lines,
        }
        return self.env['report'].render('elitum_financiero.reporte_pago_programado', docargs)


# MARZ
class ReporteComprobanteEgreso(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_comprobante_egreso'

    def get_cheque_emitido(self, banco, cheque):
        domain = [
            ('banco', '=', banco.id),
            ('name', '=', cheque)
        ]
        cheque = self.env['cheques.eliterp'].search(domain)
        return cheque

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.voucher',
            'docs': self.env['account.voucher'].browse(docids),
            'data': data,
            'get_cheque_emitido': self.get_cheque_emitido,
            'get_amount_to_word': self.env['report.elitum_contabilidad.reporte_factura_cliente'].get_amount_to_word,
            'get_lugar_fecha': self.env['report.elitum_contabilidad.reporte_cheque_matricial'].get_lugar_fecha,
        }
        return self.env['report'].render('elitum_financiero.reporte_comprobante_egreso', docargs)


class ReporteCuentasPorCobrarCompleto(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_cuentas_cobrar_completo_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.cuentas.cobrar',
            'docs': self.env['reporte.cuentas.cobrar'].browse(docids),
            'data': data,
            'fecha_actual': fields.date.today(),
            'get_lines': self.env['reporte.cuentas.cobrar'].get_lines
        }
        return self.env['report'].render('elitum_financiero.reporte_cuentas_cobrar_completo_pdf', docargs)


class ReporteCuentasPorPagarCompleto(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_cuentas_pagar_completo_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.cuentas.pagar',
            'docs': self.env['reporte.cuentas.pagar'].browse(docids),
            'data': data,
            'fecha_actual': fields.date.today(),
            'get_lines': self.env['reporte.cuentas.pagar'].get_lines
        }
        return self.env['report'].render('elitum_financiero.reporte_cuentas_pagar_completo_pdf', docargs)


class ReporteChequesRecibidos(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_cheques_recibidos_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.cheques.recibidos',
            'docs': self.env['reporte.cheques.recibidos'].browse(docids),
            'data': data,
            'fecha_actual': fields.date.today(),
            'get_lines': self.env['reporte.cheques.recibidos'].get_lines
        }
        return self.env['report'].render('elitum_financiero.reporte_cheques_recibidos_pdf', docargs)


class ReporteChequeEmitidos(models.AbstractModel):
    _name = 'report.elitum_financiero.reporte_cheques_emitidos_pdf'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'reporte.cheques.emitidos',
            'docs': self.env['reporte.cheques.emitidos'].browse(docids),
            'data': data,
            'fecha_actual': fields.date.today(),
            'get_lines': self.env['reporte.cheques.emitidos'].get_lines
        }
        return self.env['report'].render('elitum_financiero.reporte_cheques_emitidos_pdf', docargs)
