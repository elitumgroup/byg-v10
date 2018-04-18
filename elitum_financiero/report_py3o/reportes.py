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

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.report import report_sxw
import logging

_logger = logging.getLogger(__name__)


class ParserFinanciero(models.TransientModel):
    _inherit = "py3o.report"

    @api.multi
    def _extend_parser_context(self, context_instance, report_xml):
        if 'reporte_cuentas_pagar' in self._context:
            reporte = self.env['reporte.cuentas.pagar'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
            })
        if 'reporte_cuentas_cobrar' in self._context:
            reporte = self.env['reporte.cuentas.cobrar'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
            })
        if 'reporte_cheques_recibidos' in self._context:
            reporte = self.env['reporte.cheques.recibidos'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'cliente': "Todos" if self._context['cliente'] == False else self.env['res.partner'].browse(
                    self._context['cliente']).name,
                'banco': "Todos" if self._context['banco'] == False else self.env['res.bank'].browse(
                    self._context['banco']).name,
                'fecha_actual': fields.date.today(),
                'total': sum(line['valor'] for line in lines)
            })
        if 'reporte_cheques_emitidos' in self._context:
            reporte = self.env['reporte.cheques.emitidos'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines': lines,
                'banco': "Todos" if self._context['banco'] == False else self.env['res.bank'].browse(
                    self._context['banco']).name,
                'fecha_actual': fields.date.today(),
                'total': sum(line['valor'] for line in lines)
            })
        # MARZ
        if 'reporte_pagos_programados' in self._context:
            reporte = self.env['reporte.pagos.programados'].browse(self._context['active_id'])
            lines = reporte.get_lines(context_instance.localcontext)
            context_instance.localcontext.update({
                'forma_pago': self._context['forma_pago'],
                'get_lines': lines,
                'fecha_actual': fields.date.today(),
                'total_pago': sum(line['valor_pago'] for line in lines)
            })
        # Fin MARZ
        res = super(ParserFinanciero, self)._extend_parser_context(context_instance, report_xml)
        return res


class ReporteCuentasCobrar(models.TransientModel):
    _name = 'reporte.cuentas.cobrar'

    _description = 'Reporte Cuentas por Cobrar'

    def get_estado(self, estado):
        if estado == 'invoice':
            return "Facturado"
        if estado == 'order':
            return "Emitido"
        if estado == 'done':
            return "Cerrado"

    def get_lines(self, context):
        data = []
        arg = []
        if context['tipo_cliente'] != 'todos':
            if isinstance(context['cliente'], int):
                arg.append(('partner_id', '=', context['cliente']))
            else:
                arg.append(('partner_id', '=', context['cliente'].id))
        if context['estado'] != 'todos':
            arg.append(('date_due', '<=', fields.date.today()))
        arg.append(('date_invoice', '>=', context['fecha_inicio']))
        arg.append(('date_invoice', '<=', context['fecha_fin']))
        arg.append(('state', '=', 'open'))  # MARZ, Soló pendientes de cobro
        arg.append(('type', '=', 'out_invoice'))
        facturas = self.env['account.invoice'].search(arg)
        count = 0
        for factura in facturas:
            count += 1
            fecha_vencimiento = datetime.strptime(factura.date_due, "%Y-%m-%d").date()
            morosidad = 0
            dias_vencer = 0
            vencido = False
            vencer = False
            if factura.residual != 0.00:
                if fields.date.today() > fecha_vencimiento:
                    morosidad = (fields.date.today() - fecha_vencimiento).days
                    vencido = True
            if factura.residual != 0.00:
                if fecha_vencimiento < fields.date.today():
                    vencer = True
                    dias_vencer = (fecha_vencimiento - fields.date.today()).days
            valor = factura.amount_total_signed
            data.append({
                'cliente': factura.partner_id.name,
                'numero': factura.numero_factura_interno,
                'valor': valor,
                'saldo_pendiente': factura.residual,
                'fecha_emision': factura.date_invoice,
                'fecha_vencimiento': factura.date_due,
                'morosidad': morosidad,
            })
            if context['tipo_reporte'] == 'completo':
                data[-1].update(
                    {'vencer_30': valor if vencer == True and (dias_vencer >= 1 and dias_vencer <= 30) else float(0.00),
                     'vencer_90': valor if vencer == True and (dias_vencer >= 31 and dias_vencer <= 90) else 0.00,
                     'vencer_180': valor if vencer == True and (dias_vencer >= 91 and dias_vencer <= 180) else 0.00,
                     'vencer_360': valor if vencer == True and (dias_vencer >= 181 and dias_vencer <= 360) else 0.00,
                     'vencer_mayor': valor if vencer == True and (dias_vencer > 360) else 0.00,
                     'vencido_30': valor if vencido == True and (morosidad >= 1 and morosidad <= 30) else 0.00,
                     'vencido_90': valor if vencido == True and (morosidad >= 31 and morosidad <= 90) else 0.00,
                     'vencido_180': valor if vencido == True and (morosidad >= 91 and morosidad <= 180) else 0.00,
                     'vencido_360': valor if vencido == True and (morosidad >= 181 and morosidad <= 360) else 0.00,
                     'vencido_mayor': valor if vencido == True and (morosidad > 360) else 0.00, })
        return data

    def imprimir_reporte_cuentas_cobrar(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_financiero.reporte_cuentas_cobrar' if self.tipo_reporte == 'resumido' else 'elitum_financiero.reporte_cuentas_cobrar_completo',
            'datas': {'ids': reporte},
            'context': {
                'reporte_cuentas_cobrar': True,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'tipo_cliente': self.tipo_cliente,
                'cliente': self.cliente.id if len(self.cliente) != 0 else False,
                'estado': self.estado,
                'tipo_reporte': self.tipo_reporte,
                'morosidad': self.morosidad,
            }
        }
        return result

    # MARZ
    def imprimir_reporte_cuentas_cobrar_pdf(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_cuentas_cobrar_completo_pdf')

    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    tipo_reporte = fields.Selection([('completo', 'Completo'), ('resumido', 'Resumido')], default='completo')
    estado = fields.Selection([('todas', 'Todas'), ('vencidas', 'Vencidas')], default='todas')
    morosidad = fields.Integer('Morosidad')
    tipo_cliente = fields.Selection([('todos', 'Todos'), ('cliente', 'Individual')], 'Tipo de Cliente', default='todos')
    cliente = fields.Many2one('res.partner', 'Cliente')


class ReporteCuentasPagar(models.TransientModel):
    _name = 'reporte.cuentas.pagar'

    _description = 'Reporte Cuentas por Pagar'

    def get_estado(self, estado):
        if estado == 'invoice':
            return "Facturado"
        if estado == 'order':
            return "Emitido"
        if estado == 'done':
            return "Cerrado"

    def get_lines(self, context):
        data = []
        arg = []
        if context['tipo_proveedor'] != 'todos':
            if isinstance(context['proveedor'], int):
                arg.append(('partner_id', '=', context['proveedor']))
            else:
                arg.append(('partner_id', '=', context['proveedor'].id))
        if context['estado'] != 'todos':
            arg.append(('date_due', '<=', fields.date.today()))
        arg.append(('date_invoice', '>=', context['fecha_inicio']))
        arg.append(('date_invoice', '<=', context['fecha_fin']))
        arg.append(('state', 'in', ('open', 'paid')))
        arg.append(('type', '=', 'in_invoice'))
        facturas = self.env['account.invoice'].search(arg)
        count = 0
        for factura in facturas:
            if factura.residual == 0.00:
                continue
            count += 1
            fecha_vencimiento = datetime.strptime(factura.date_due, "%Y-%m-%d").date()
            nota_credito = self.env['account.invoice'].search([('invoice_id_ref', '=', factura.id)])
            morosidad = 0
            dias_vencer = 0
            vencido = False
            vencer = False
            if factura.residual != 0.00:
                if fields.date.today() > fecha_vencimiento:
                    morosidad = (fields.date.today() - fecha_vencimiento).days
                    vencido = True
            if factura.residual != 0.00:
                if fecha_vencimiento < fields.date.today():
                    vencer = True
                    dias_vencer = (fecha_vencimiento - fields.date.today()).days
            valor = factura.amount_total
            saldo_p = factura.residual  # MARZ
            if fecha_vencimiento > fields.date.today():
                morosidad = fields.date.today() - fecha_vencimiento
            data.append({
                'proveedor': factura.partner_id.name,
                'numero': factura.numero_factura_interno,
                'subtotal': factura.amount_untaxed,
                'iva': factura.amount_tax,
                'total': valor,
                'numero_nota_credito': nota_credito.numero_factura_interno if len(nota_credito) > 0 else "-",
                'valor_nota_credito': nota_credito.amount_untaxed if len(nota_credito) > 0 else 0.00,
                'saldo_pendiente': factura.residual,
                'fecha_emision': factura.date_invoice,
                'fecha_vencimiento': factura.date_due,
                'morosidad': morosidad,
            })
            if context['tipo_reporte'] == 'completo':
                data[-1].update(
                    {
                        'vencer_30': saldo_p if vencer and (dias_vencer >= 1 and dias_vencer <= 30) else float(0.00),
                        'vencer_90': saldo_p if vencer and (dias_vencer >= 31 and dias_vencer <= 90) else 0.00,
                        'vencer_180': saldo_p if vencer and (dias_vencer >= 91 and dias_vencer <= 180) else 0.00,
                        'vencer_360': saldo_p if vencer and (dias_vencer >= 181 and dias_vencer <= 360) else 0.00,
                        'vencer_mayor': saldo_p if vencer and (dias_vencer > 360) else 0.00,
                        'vencido_30': saldo_p if vencido and (morosidad >= 1 and morosidad <= 30) else 0.00,
                        'vencido_90': saldo_p if vencido and (morosidad >= 31 and morosidad <= 90) else 0.00,
                        'vencido_180': saldo_p if vencido and (morosidad >= 91 and morosidad <= 180) else 0.00,
                        'vencido_360': saldo_p if vencido and (morosidad >= 181 and morosidad <= 360) else 0.00,
                        'vencido_mayor': saldo_p if vencido and (morosidad > 360) else 0.00,
                    })
        return data

    def imprimir_reporte_cuentas_pagar(self):
        reporte = []
        reporte.append(self.id)
        result = {'type': 'ir.actions.report.xml',
                  'report_name': 'elitum_financiero.reporte_cuentas_pagar' if self.tipo_reporte == 'resumido' else 'elitum_financiero.reporte_cuentas_pagar_completo',
                  'datas': {'ids': reporte},
                  'context': {
                      'reporte_cuentas_pagar': True,
                      'fecha_inicio': self.fecha_inicio,
                      'fecha_fin': self.fecha_fin,
                      'tipo_proveedor': self.tipo_proveedor,
                      'proveedor': self.proveedor.id if len(self.proveedor) != 0 else False,
                      'estado': self.estado,
                      'tipo_reporte': self.tipo_reporte,
                      'morosidad': self.morosidad,
                  }
                  }
        return result

    # MARZ
    def imprimir_reporte_cuentas_pagar_pdf(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_cuentas_pagar_completo_pdf')

    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    tipo_reporte = fields.Selection([('completo', 'Completo'), ('resumido', 'Resumido')], default='completo')
    estado = fields.Selection([('todas', 'Todas'), ('vencidas', 'Vencidas')], default='todas')
    morosidad = fields.Integer('Morosidad')
    tipo_proveedor = fields.Selection([('todos', 'Todos'), ('proveedor', 'Individual')], 'Tipo de Proveedor',
                                      default='todos')
    proveedor = fields.Many2one('res.partner', 'Proveedor')


class ReporteChequesRecibidos(models.TransientModel):
    _name = 'reporte.cheques.recibidos'

    _description = 'Reporte Cheques Recibidos'

    def probando(self, numero):
        decimals = 2
        sep = ","
        return "%s%s%0*u" % (int(numero), sep, decimals, (10 ** decimals) * (numero - int(numero)))

    def get_estado(self, estado):
        if estado == 'invoice':
            return "Facturado"
        if estado == 'order':
            return "Emitido"
        if estado == 'done':
            return "Cerrado"

    def get_facturas(self, facturas):
        numero_factura = ""
        count = 0
        for f in facturas:
            if count == 0:
                numero_factura = numero_factura + f.name[-5:]
                count = count + 1
            else:
                numero_factura = numero_factura + "-" + f.name[-5:]
        return numero_factura

    def get_lines(self, context):
        data = []
        arg = []
        if context['tipo_cliente'] != 'todos':
            if isinstance(context['cliente'], int):
                arg.append(('partner_id', '=', context['cliente']))
            else:
                arg.append(('partner_id', '=', context['cliente'].id))
        arg.append(('voucher_type', '=', 'sale'))
        vouchers = self.env['account.voucher'].search(arg)
        for voucher in vouchers:
            facturas = self.get_facturas(voucher.lineas_cobros_facturas)
            for line in voucher.lineas_tipos_pagos:
                if (line.tipo_de_pagos == 'bank'):
                    if line.time_type == 'corriente':
                        fecha = voucher.date
                    else:
                        fecha = line.date_created_eliterp
                    if (fecha >= context['fecha_inicio'] and fecha <= context['fecha_fin']):
                        data.append({
                            'fecha_recibido': voucher.date,
                            'fecha_documento': voucher.date if line.time_type == 'corriente' else line.date_created_eliterp,
                            'fecha_cobro': voucher.date if line.time_type == 'corriente' else line.date_due,
                            'cliente': voucher.partner_id.name,
                            'facturas': facturas,
                            'banco_emisor': line.banco.name,
                            'numero_cheque': line.numero_cheque,
                            'valor': line.amount,
                        })
        return data

    def imprimir_reporte_cheques_recibidos(self):
        reporte = []
        reporte.append(self.id)
        result = {'type': 'ir.actions.report.xml',
                  'report_name': 'elitum_financiero.reporte_cheques_recibidos',
                  'datas': {'ids': reporte},
                  'context': {
                      'reporte_cheques_recibidos': True,
                      'fecha_inicio': self.fecha_inicio,
                      'fecha_fin': self.fecha_fin,
                      'tipo_cliente': self.tipo_cliente,
                      'cliente': self.cliente.id if len(self.cliente) != 0 else False,
                      'tipo_banco': self.tipo_banco,
                      'banco': self.banco.id if len(self.banco) != 0 else False,
                  }
                  }
        return result

    # MARZ
    def imprimir_reporte_cheques_recibidos_pdf(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_cheques_recibidos_pdf')

    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    tipo_cliente = fields.Selection([('todos', 'Todos'), ('cliente', 'Individual')], 'Tipo de Cliente', default='todos')
    cliente = fields.Many2one('res.partner', 'Cliente')
    tipo_banco = fields.Selection([('todos', 'Todos'), ('banco', 'Individual')], 'Tipo de Asesor', default='todos')
    banco = fields.Many2one('res.bank', 'Banco')


class ReporteChequesEmitidos(models.TransientModel):
    _name = 'reporte.cheques.emitidos'

    _description = 'Reporte Cheques Emitidos'

    def get_estado(self, estado):
        if estado == 'draft':
            return "Borrador"
        if estado == 'posted':
            return "Contabilizado"
        if estado == 'cancel':
            return "Anulado"

    def get_lines(self, context):
        data = []
        arg = []
        if context['tipo_cheque'] == 'varios':
            arg.append(('beneficiario_proveedor', '=', 'beneficiario'))
        if context['tipo_cheque'] == 'proveedor':
            arg.append(('beneficiario_proveedor', '=', 'supplier'))
        if context['tipo_cheque'] == 'caja_chica':
            arg.append(('beneficiario_proveedor', '=', 'caja_chica'))
        # MARZ
        if context['tipo_cheque'] == 'solicitud_pago':
            arg.append(('beneficiario_proveedor', '=', 'caja_chica'))
        if context['tipo_cheque'] == 'caja_chica':
            arg.append(('beneficiario_proveedor', '=', 'caja_chica'))
        arg.append(('voucher_type', '=', 'purchase'))
        arg.append(('post_date', '>=', context['fecha_inicio']))
        arg.append(('post_date', '<=', context['fecha_fin']))
        vouchers = self.env['account.voucher'].search(arg)
        for voucher in vouchers:
            data.append({
                'numero_cheque': voucher.numero_cheque,
                'banco': voucher.banco.name,
                'fecha_emision': voucher.date,
                'fecha_pago': voucher.post_date,
                'beneficiario': voucher.beneficiario,
                'concepto': voucher.concepto_pago,
                'valor': voucher.cantidad,
                'estado': self.get_estado(voucher.state),
            })

        data = sorted(data, key=lambda x: (x['banco'], x['numero_cheque']))
        return data

    def imprimir_reporte_cheques_emitidos(self):
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_financiero.reporte_cheques_emitidos',
            'datas': {'ids': reporte},
            'context': {
                'reporte_cheques_emitidos': True,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'banco': self.banco.id if len(self.banco) != 0 else False,
                'tipo_cheque': self.tipo_cheque, }
        }
        return result

    # MARZ
    def imprimir_reporte_cheques_emitidos_pdf(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_cheques_emitidos_pdf')

    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    tipo_cheque = fields.Selection([('todos', 'Todos'),
                                    ('varios', 'Varios'),
                                    ('proveedor', 'Proveedor'),
                                    ('caja_chica', 'Caja Chica'),
                                    ('solicitud_pago', 'Solicitud de Pago'),
                                    ('viaticos', 'Solicitud de Viáticos')], 'Tipo de Cheque', default='todos')
    tipo_banco = fields.Selection([('todos', 'Todos'), ('banco', 'Individual')], 'Tipo de Asesor', default='todos')
    banco = fields.Many2one('res.bank', 'Banco')


# MARZ
# Reporte de Pagos Programados
class ReportePagosProgramados(models.TransientModel):
    _name = 'reporte.pagos.programados'

    _description = 'Reporte Pagos Programados'

    def get_days_mora(self, vencimiento):
        morosidad = 0
        morosidad = (fields.date.today() - vencimiento).days
        return str(morosidad)

    def get_lines(self, context):
        data = []
        arg = []
        if context['forma_pago'] != 'todas':
            arg.append(('way_to_pay', '=', context['forma_pago']))
        pays = self.env['account.invoice.payment.scheduled'].search(arg)
        for pay in pays:
            fecha_pago = pay.fecha
            if (fecha_pago >= context['fecha_inicio'] and fecha_pago <= context['fecha_fin']):
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

    def imprimir_reporte_pagos_programados_xls(self):
        begin = self.fecha_inicio
        end = self.fecha_fin
        way_to_pay = self.forma_pago
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_financiero.reporte_pagos_programados',
            'datas': {'ids': reporte},
            'context': {
                'reporte_pagos_programados': True,
                'fecha_inicio': begin,
                'fecha_fin': end,
                'forma_pago': way_to_pay,
            }
        }
        return result

    def imprimir_reporte_pagos_programados_pdf(self):
        return self.env['report'].get_action(self, 'elitum_financiero.reporte_pago_programado')

    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    forma_pago = fields.Selection([('todas', 'Todas'), ('efectivo', 'Efectivo'), ('cheque', 'Cheque')], 'Forma de Pago',
                                  default='todas')
