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
from operator import itemgetter
from datetime import datetime
import logging
from odoo.exceptions import except_orm

_logger = logging.getLogger(__name__)


class ParserSRI(models.TransientModel):
    _inherit = "py3o.report"

    @api.multi
    def _extend_parser_context(self, context_instance, report_xml):
        if 'reporte_103_104' in self._context:
            reporte = self.env['reporte.103.104'].browse(self._context['active_id'])
            lines_compras = reporte.get_lines_compras(context_instance.localcontext)
            lines_ventas = reporte.get_lines_ventas(context_instance.localcontext)
            lines_anulados = reporte.get_lines_anulados(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_lines_compras': lines_compras,
                'get_lines_ventas': lines_ventas,
                'get_lines_anulados': lines_anulados,
                'get_detalle_codigo': reporte.get_detalle_codigo(),
                'fecha_actual': fields.date.today(),
                # Totales de Compras
                'total_base_14_compras': sum(line['base_iva'] for line in lines_compras),
                'total_base_0_compras': sum(line['base_0'] for line in lines_compras),
                'total_ice_compras': sum(line['ice'] for line in lines_compras),
                'total_base_no_iva_compras': sum(line['base_no_iva'] for line in lines_compras),
                'total_ret_fte_compras': sum(line['monto_renta'] for line in lines_compras),
                'total_base_iva_compras': sum(line['retencion_base_iva'] for line in lines_compras),
                'total_ret_iv_compras': sum(line['monto_iva'] for line in lines_compras),
                'total_factura_compras': sum(line['total_factura'] for line in lines_compras),
                # Totales de Ventas
                'total_base_14_ventas': sum(line['base_iva'] for line in lines_ventas),
                'total_base_0_ventas': sum(line['base_0'] for line in lines_ventas),
                'total_ice_ventas': sum(line['ice'] for line in lines_ventas),
                'total_base_no_iva_ventas': sum(line['base_no_iva'] for line in lines_ventas),
                'total_ret_fte_ventas': sum(line['monto_renta'] for line in lines_ventas),
                'total_base_iva_ventas': sum(line['retencion_base_iva'] for line in lines_ventas),
                'total_ret_iv_ventas': sum(line['monto_iva'] for line in lines_ventas),
                'total_factura_ventas': sum(line['total_factura'] for line in lines_ventas),
                'total_a_pagar_impuestos': sum(line['monto_renta'] for line in lines_compras) + sum(
                    line['monto_renta'] for line in lines_ventas),
                'total_iva_mes_actual': 0.00
            })
            fecha = datetime.strptime(context_instance.localcontext['fecha_inicio'], "%Y-%m-%d")
            mes = fecha.month - 1
            year = fecha.year
            if mes == 0:  # Soló para el mes de enero
                mes = 12
                year = year - 1
            credito_tributario = self.env['credito.tributario'].search(
                [('mes', '=', mes), ('ano', '=', year)])
            ano_contable = self.env['account.period'].search([('ano_contable', '=', fecha.year)])
            if len(ano_contable) == 0:
                return super(ParserSRI, self)._extend_parser_context(context_instance, report_xml)
            periodo = ano_contable.lineas_periodo.filtered(lambda x: x.code == fecha.month)
            valor_iva_tributario = 0.00
            valor_renta_tributario = 0.00
            if len(credito_tributario) != 0:
                valor_iva_tributario = credito_tributario.valor
                valor_renta_tributario = credito_tributario.valor_renta
            context = context_instance.localcontext
            # MARZ
            credito_tributario_new = self.env['credito.tributario'].search(
                [('mes', '=', fecha.month), ('ano', '=', fecha.year)])
            total_iva = 0.00
            total_renta_iva = 0.00
            resta_iva = context['total_base_iva_ventas'] - context['total_base_iva_compras']
            # 1
            if resta_iva <= 0:
                total_iva = resta_iva
                context_instance.localcontext.update({'total_iva_mes_actual': context['total_ret_iv_compras']})
            # 2
            if resta_iva > 0:
                total_iva = resta_iva - valor_iva_tributario + context['total_ret_iv_compras']
                context_instance.localcontext.update({'total_iva_mes_actual': total_iva})
                total_iva = 0.00
            # 3
            if valor_iva_tributario == 0:
                total_iva = resta_iva + context['total_ret_iv_compras']- valor_renta_tributario
                context_instance.localcontext.update({'total_iva_mes_actual': total_iva})
                total_iva = 0.00
                total_renta_iva = 0.00
            else:
                total_renta_iva = valor_renta_tributario - context['total_ret_iv_ventas']
            # Si no existe el nuevo registro, lo creo
            if len(credito_tributario_new) == 0:
                self.env['credito.tributario'].create({
                    'ano_contable': ano_contable.id,
                    'period_id': periodo.id,
                    'valor': total_iva,
                    'valor_renta': total_renta_iva,
                })
            # Si existe la actualizó
            else:
                credito_tributario_new.update({
                    'valor': total_iva,
                    'valor_renta': total_renta_iva
                })
            context_instance.localcontext.update(
                {'total_a_pagar_impuestos': context['total_ret_fte_compras'] + context['total_iva_mes_actual']})
        # MARZ
        if 'reporte_ats_plantilla' in self._context:
            reporte = self.env['eliterp.reporte.ats.plantilla'].browse(self._context['active_id'])
            line_general = reporte.get_line_general(context_instance.localcontext)
            lines_compras = reporte.get_lines_compras(context_instance.localcontext)
            lines_pagos = reporte.get_lines_pagos()
            lines_ventas = reporte.get_lines_ventas(context_instance.localcontext)
            lines_cobros = reporte.get_lines_cobros()
            lines_establecimientos = reporte.get_lines_establecimientos(context_instance.localcontext)
            lines_anulados = reporte.get_lines_anulados(context_instance.localcontext)
            context_instance.localcontext.update({
                'get_line_general': line_general,
                'get_lines_compras': lines_compras,
                'get_lines_pagos': lines_pagos,
                'get_lines_ventas': lines_ventas,
                'get_lines_cobros': lines_cobros,
                'get_lines_establecimientos': lines_establecimientos,
                'get_lines_anulados': lines_anulados
            })
        res = super(ParserSRI, self)._extend_parser_context(context_instance, report_xml)
        return res


class Reporte103104(models.TransientModel):
    _name = 'reporte.103.104'

    _description = 'Reporte 103 104'

    def get_estado(self, estado):
        if estado == 'invoice':
            return "Facturado"
        if estado == 'order':
            return "Emitido"
        if estado == 'done':
            return "Cerrado"

    def get_detalle_codigo(self):
        return RETENCIONES

    def get_lines_compras(self, context):
        data = []
        arg = []
        arg.append(('date_invoice', '>=', context['fecha_inicio']))
        arg.append(('date_invoice', '<=', context['fecha_fin']))
        arg.append(('state', 'not in', ('draft', 'cancel')))
        arg.append(('type', 'in', ('in_invoice', 'in_sale_note')))
        facturas = self.env['account.invoice'].search(arg)
        count = 0
        for factura in facturas:
            count_factura = 0
            for line in factura.invoice_line_ids:
                data.append({
                    'tipo': "F" if factura.type == 'in_invoice' else "N",
                    'establecimiento': factura.numero_establecimiento,
                    'emision': factura.punto_emision,
                    'secuencia': factura.numero_factura,
                    'fecha_emision': factura.date_invoice,
                    'numero_retencion': factura.numero_retencion if factura.numero_retencion else "--",
                    'descripcion': line.name,
                    'razon_social': factura.partner_id.name,
                    'ruc': factura.partner_id.vat_eliterp,
                    'autorizacion': factura.numero_autorizacion,
                    'sustento_codigo': factura.sustento_tributario.codigo,
                    'base_iva': 0.00,
                    'base_0': 0.00,
                    'ice': 0.00,
                    'base_no_iva': 0.00,
                    'codigo_renta': 0,
                    'porcentaje_renta': 0,
                    'monto_renta': 0.00,
                    'retencion_base_iva': factura.amount_tax if count_factura == 0 else 0.00,
                    'codigo_iva': 0,
                    'porcentaje_iva': 0,
                    'monto_iva': 0.00,
                    'total_factura': 0.00,
                })
                count_factura = 1
                if len(line.invoice_line_tax_ids) == 0:
                    data[-1]['base_no_iva'] = line.price_subtotal
                else:
                    for tax in line.invoice_line_tax_ids:
                        if tax.amount > 0:
                            data[-1]['base_iva'] = line.price_subtotal
                        if tax.amount == 0:
                            data[-1]['base_0'] = line.price_subtotal
            renta = []
            iva = []
            for line_retencion in factura.withhold_id.line_tax_withhold:
                if line_retencion.tipo_retencion == 'renta':
                    renta.append(line_retencion)
                if line_retencion.tipo_retencion == 'iva':
                    iva.append(line_retencion)
            if len(renta) == 2:
                data.append({
                    'tipo': "F" if factura.type == 'in_invoice' else "N",
                    'establecimiento': factura.numero_establecimiento,
                    'emision': factura.punto_emision,
                    'secuencia': factura.numero_factura,
                    'fecha_emision': factura.date_invoice,
                    'numero_retencion': factura.numero_retencion,
                    'descripcion': line.name,
                    'razon_social': factura.partner_id.name,
                    'ruc': factura.partner_id.vat_eliterp,
                    'autorizacion': factura.numero_autorizacion,
                    'sustento_codigo': factura.sustento_tributario.codigo,
                    'base_iva': 0.00,
                    'base_0': 0.00,
                    'ice': 0.00,
                    'base_no_iva': 0.00,
                    'codigo_renta': 0,
                    'porcentaje_renta': 0,
                    'monto_renta': 0.00,
                    'retencion_base_iva': 0.00,
                    'codigo_iva': 0,
                    'porcentaje_iva': 0,
                    'monto_iva': 0.00,
                    'total_factura': 0.00,
                })
            count = -1
            for r in renta:
                data[count]['codigo_renta'] = r.retencion.code_name
                data[count]['porcentaje_renta'] = r.retencion.amount
                data[count]['monto_renta'] = r.monto if factura.state != 'cancel' else 0.00
                count = count - 1
                if RETENCIONES == []:
                    RETENCIONES.append({'codigo': r.retencion.code_name,
                                        'sub_total': r.base_imponible if factura.state != 'cancel' else 0.00,
                                        'monto': r.monto if factura.state != 'cancel' else 0.00,
                                        'tipo': "renta"})
                else:
                    esta_el_codigo_renta = any(d['codigo'] == r.retencion.code_name for d in RETENCIONES)
                    if esta_el_codigo_renta:
                        index = map(itemgetter('codigo'), RETENCIONES).index(r.retencion.code_name)
                        RETENCIONES[index]['monto'] = RETENCIONES[index]['monto'] + (
                            r.monto if factura.state != 'cancel' else 0.00)
                        RETENCIONES[index]['sub_total'] = RETENCIONES[index]['sub_total'] + (
                            r.base_imponible if factura.state != 'cancel' else 0.00)
                    else:
                        RETENCIONES.append({'codigo': r.retencion.code_name,
                                            'sub_total': r.base_imponible if factura.state != 'cancel' else 0.00,
                                            'monto': r.monto if factura.state != 'cancel' else 0.00,
                                            'tipo': "renta"})
            count = -1
            for i in iva:
                data[count]['codigo_iva'] = i.retencion.code_name
                data[count]['porcentaje_iva'] = i.retencion.amount
                data[count]['monto_iva'] = i.monto if factura.state != 'cancel' else 0.00
                count = count - 1
                if RETENCIONES == []:
                    RETENCIONES.append({'codigo': i.retencion.code_name,
                                        'sub_total': i.base_imponible if factura.state != 'cancel' else 0.00,
                                        'monto': i.monto if factura.state != 'cancel' else 0.00,
                                        'tipo': "iva"})
                else:
                    esta_el_codigo_iva = any(d['codigo'] == i.retencion.code_name for d in RETENCIONES)
                    if esta_el_codigo_iva:
                        index = map(itemgetter('codigo'), RETENCIONES).index(i.retencion.code_name)
                        RETENCIONES[index]['monto'] = RETENCIONES[index]['monto'] + (
                            i.monto if factura.state != 'cancel' else 0.00)
                        RETENCIONES[index]['sub_total'] = RETENCIONES[index]['monto'] + (
                            i.base_imponible if factura.state != 'cancel' else 0.00)
                    else:
                        RETENCIONES.append({'codigo': i.retencion.code_name,
                                            'sub_total': i.base_imponible if factura.state != 'cancel' else 0.00,
                                            'monto': i.monto if factura.state != 'cancel' else 0.00,
                                            'tipo': "iva"})
            data[-1]['total_factura'] = factura.amount_total
        return data

    def get_lines_ventas(self, context):
        data = []
        arg = []
        arg.append(('date_invoice', '>=', context['fecha_inicio']))
        arg.append(('date_invoice', '<=', context['fecha_fin']))
        arg.append(('state', 'not in', ('draft', 'cancel')))
        arg.append(('type', '=', 'out_invoice'))
        facturas = self.env['account.invoice'].search(arg)
        count = 0
        autorizacion = self.env['autorizacion.sri'].search([('tipo_comprobante', '=', 4), ('state', '=', 'activo')])[0]
        for factura in facturas:
            count_factura = 0
            for line in factura.invoice_line_ids:
                data.append({
                    'tipo': "F" if factura.type == 'out_invoice' else "N",
                    'establecimiento': autorizacion.numero_establecimiento,
                    'emision': autorizacion.punto_emision,
                    'secuencia': ((factura.numero_factura).split("-"))[2],
                    'fecha_emision': factura.date_invoice,
                    'numero_retencion': factura.numero_retencion if factura.numero_retencion else "--",
                    'descripcion': line.name,
                    'razon_social': factura.partner_id.name,
                    'ruc': factura.partner_id.vat_eliterp,
                    'autorizacion': autorizacion.numero_autorizacion,
                    'sustento_codigo': factura.sustento_tributario.codigo if factura.sustento_tributario.codigo else "--",
                    'base_iva': 0.00,
                    'base_0': 0.00,
                    'ice': 0.00,
                    'base_no_iva': 0.00,
                    'codigo_renta': 0,
                    'porcentaje_renta': 0,
                    'monto_renta': 0.00,
                    'retencion_base_iva': factura.amount_tax if count_factura == 0 else 0.00,
                    'codigo_iva': 0,
                    'porcentaje_iva': 0,
                    'monto_iva': 0.00,
                    'total_factura': 0.00,
                })
                count_factura = 1
                if len(line.invoice_line_tax_ids) == 0:
                    data[-1]['base_no_iva'] = line.price_subtotal
                else:
                    for tax in line.invoice_line_tax_ids:
                        if tax.amount > 0:
                            data[-1]['base_iva'] = line.price_subtotal
                        if tax.amount == 0:
                            data[-1]['base_0'] = line.price_subtotal
            renta = []
            iva = []
            for line in factura.withhold_id.line_tax_withhold:
                if line.tipo_retencion == 'renta':
                    renta.append(line)
                if line.tipo_retencion == 'iva':
                    iva.append(line)
            count = -1
            for r in renta:
                data[count]['codigo_renta'] = r.retencion.code_name
                data[count]['porcentaje_renta'] = r.retencion.amount
                data[count]['monto_renta'] = r.monto
                count = count - 1
            count = -1
            for i in iva:
                data[count]['codigo_iva'] = i.retencion.code_name
                data[count]['porcentaje_iva'] = i.retencion.amount
                data[count]['monto_iva'] = i.monto
                count = count - 1
            data[-1]['total_factura'] = factura.amount_total
        return data

    def get_lines_anulados(self, context):
        data = []
        arg = []
        autorizaciones = self.env['autorizacion.sri'].search([('state', '=', 'activo')])
        for autorizacion in autorizaciones:
            arg = []
            if autorizacion.tipo_comprobante in (2, 3):
                arg.append(('date_invoice', '>=', context['fecha_inicio']))
                arg.append(('date_invoice', '<=', context['fecha_fin']))
                arg.append(('state', '=', 'cancel'))
                if autorizacion.tipo_comprobante == 1:
                    arg.append(('type', '=', 'out_invoice'))
                if autorizacion.tipo_comprobante == 3:
                    arg.append(('type', '=', 'out_refund'))
                facturas = self.env['account.invoice'].search(arg)
                for factura in facturas:
                    data.append({'tipo': "F" if autorizacion.tipo_comprobante == 2 else "N",
                                 'establecimiento': ((factura.numero_factura).split("-"))[0],
                                 'emision': ((factura.numero_factura).split("-"))[1],
                                 'secuencia': ((factura.numero_factura).split("-"))[2],
                                 'fecha_emision': factura.date_invoice,
                                 'razon_social': factura.partner_id.name})
            if autorizacion.tipo_comprobante == 1:
                arg.append(('fecha', '>=', context['fecha_inicio']))
                arg.append(('fecha', '<=', context['fecha_fin']))
                arg.append(('state', '=', 'cancel'))
                arg.append(('type', '=', 'purchase'))
                retenciones = self.env['tax.withhold'].search(arg)
                for retencion in retenciones:
                    if retencion.if_secuencial == True:
                        partir = (retencion.name_retencion).split("-")  # MARZ
                        data.append({
                            'tipo': "R",
                            'establecimiento': partir[0] if len(partir) == 2 else '--',
                            'emision': partir[1] if len(partir) == 2 else '--',
                            'secuencia': partir[2] if len(partir) == 2 else '--',
                            'fecha_emision': retencion.fecha,
                            'razon_social': retencion.partner_id.name
                        }),
        return data

    def imprimir_reporte_103_104(self):
        global RETENCIONES
        RETENCIONES = []
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_contabilidad.reporte_103_104',
            'datas': {
                'ids': reporte
            },
            'context': {
                'reporte_103_104': True,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin
            }
        }
        return result

    fecha_inicio = fields.Date('Fecha Inicio', required=True)
    fecha_fin = fields.Date('Fecha Fin', required=True)


# MARZ
class ReporteATSPlantilla(models.TransientModel):
    _name = 'eliterp.reporte.ats.plantilla'
    _description = 'Anexo Transaccional Simplificado (Plantilla)'

    @api.multi
    def _get_company(self):
        return self.env.user.company_id.id

    def get_line_general(self, context):
        data = []
        period = self.env['lines.account.period'].search([('id', '=', context['periodo'])])
        data.append({
            'IdInformante': self.company_id.partner_id.vat_eliterp,
            'razonSocial': self.company_id.name.replace('.', ''),
            'Anio': self.env['eliterp.reporte.ats'].get_date_value(period.fecha_inicio, '%Y'),
            'Mes': self.env['eliterp.reporte.ats'].get_date_value(period.fecha_inicio, '%m'),
            'numEstabRuc': context['establecimiento'].zfill(3),
            'totalVentas': '%.2f' % self.env['eliterp.reporte.ats']._get_ventas(period)
        })
        return data

    def get_lines_compras(self, context):
        data = []
        period = self.env['lines.account.period'].search([('id', '=', context['periodo'])])
        data = self.env['eliterp.reporte.ats'].read_compras(period, context['pay_limit'])
        count = 0
        for line in data:
            count += 1
            code = 'C' + str(count)  # Código de Compra
            line.update({
                'codigo': code
            })
            # No tiene Retención
            if not line.has_key('retencion'):
                line.update({
                    'estabRetencion1': '-',
                    'ptoEmiRetencion1': '-',
                    'secRetencion1': '-',
                    'autRetencion1': '-',
                    'fechaEmiRet1': '-'
                })
            # No tienen Nota de Crédito
            if not line.has_key('nota'):
                line.update({
                    'docModificado': '-',
                    'estabModificado': '-',
                    'ptoEmiModificado': '-',
                    'secModificado': '-',
                    'autModificado': '-'
                })
            if line.has_key('pay'):
                FORMAS_PAGO.append({
                    'codigo': code,
                    'forma': line['formaPago']
                })
        return data

    def get_lines_pagos(self):
        return FORMAS_PAGO

    def get_lines_ventas(self, context):
        data = []
        period = self.env['lines.account.period'].search([('id', '=', context['periodo'])])
        data = self.env['eliterp.reporte.ats'].read_ventas(period)
        count = 0
        for line in data:
            count += 1
            code = 'V' + str(count)  # Código de Venta
            line.update({
                'codigo': code
            })
            FORMAS_COBRO.append({
                'codigo': code,
                'forma': line['formaPago']
            })
        return data

    def get_lines_cobros(self):
        return FORMAS_COBRO

    def get_lines_establecimientos(self, context):
        data = []
        period = self.env['lines.account.period'].search([('id', '=', context['periodo'])])
        data.append({
            'codEstab': '001',
            'ventasEstab': '%.2f' % self.env['eliterp.reporte.ats']._get_ventas(period),
            'ivaComp': '0.00'
        })
        return data

    def get_lines_anulados(self, context):
        data = []
        period = self.env['lines.account.period'].search([('id', '=', context['periodo'])])
        data = self.env['eliterp.reporte.ats'].read_anulados(period)
        return data

    def imprimir_ats(self):
        global FORMAS_PAGO, FORMAS_COBRO
        FORMAS_PAGO = []
        FORMAS_COBRO = []
        reporte = []
        reporte.append(self.id)
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_contabilidad.reporte_ats_plantilla',
            'datas': {
                'ids': reporte
            },
            'context': {
                'reporte_ats_plantilla': True,
                'periodo': self.period_id.id,
                'establecimiento': self.num_estab_ruc,
                'pay_limit': self.pay_limit
            }
        }
        return result

    ano_contable = fields.Many2one(
        'account.period',
        u'Año Contable',
        required=True
    )
    period_id = fields.Many2one(
        'lines.account.period',
        'Período',
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        'Companía',
        default=_get_company
    )
    num_estab_ruc = fields.Char(
        'No. Establecimiento',
        size=3,
        required=True,
        default='001'
    )
    pay_limit = fields.Float('Límite de Pago', default=1000)
