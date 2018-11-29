# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2017 Ing. Mario Rangel, Elitum Group                   #
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
import base64
import StringIO
import os
import logging
from itertools import groupby
from operator import itemgetter
from lxml import etree
from lxml.etree import DocumentInvalid
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from odoo.exceptions import except_orm
import time

STD_FORMAT = '%Y-%m-%d'

tpIdProv = {
    '04': '01',
    '05': '02',
    '06': '03',
}


class AccountAts(dict):
    """
    representación del ATS
    >>> ats.campo = 'valor'
    >>> ats['campo']
    'valor'
    """

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, item, value):
        if item in self.__dict__:
            dict.__setattr__(self, item, value)
        else:
            self.__setitem__(item, value)


class ReporteATS(models.TransientModel):
    _name = 'eliterp.reporte.ats'
    _description = 'Anexo Transaccional Simplificado'
    __logger = logging.getLogger(_name)

    def get_date_value(self, date, t='%Y'):
        return time.strftime(t, time.strptime(date, STD_FORMAT))

    def convertir_fecha(self, fecha):
        """
        fecha: '2012-12-15'
        return: '15/12/2012'
        """
        f = fecha.split('-')
        date = datetime(int(f[0]), int(f[1]), int(f[2]))
        return date.strftime('%d/%m/%Y')

    @api.multi
    def _get_company(self):
        return self.env.user.company_id.id

    @api.model
    def _get_ventas(self, period):
        '''Obtenemos total de ventas en período seleccionado'''
        sql_ventas = "SELECT type, sum(amount_untaxed) AS base \
                          FROM account_invoice \
                          WHERE type IN ('out_invoice', 'out_refund') \
                          AND state IN ('open','paid') \
                          AND date_invoice BETWEEN '%s' AND '%s'" % (period.fecha_inicio, period.fecha_cierre)
        sql_ventas += " GROUP BY type"
        self.env.cr.execute(sql_ventas)
        res = self.env.cr.fetchall()
        resultado = sum(map(lambda x: x[0] == 'out_refund' and x[1] * -1 or x[1], res))
        return resultado

    def _get_ret_iva(self, invoice):
        '''Obtenemos los valores de diferentes tipos de Retención'''
        retBien10 = 0
        retServ20 = 0
        retBien = 0
        retServ = 0
        retServ100 = 0
        withhold = invoice.withhold_id
        if withhold:
            for tax in withhold.line_tax_withhold:
                if tax.tipo_retencion == 'iva':
                    if tax.retencion.code_name == '725':
                        # Retención 30%
                        retBien += abs(tax.monto)
                    if tax.retencion.code_name == '727':
                        # Retención 70%
                        retServ += abs(tax.monto)
                    if tax.retencion.code_name == '729':
                        # Retención 100%
                        retServ100 += abs(tax.monto)
        return retBien10, retServ20, retBien, retServ, retServ100

    def process_lines(self, invoice):
        '''Obtenemos las líneas de retención tipo renta para Facturas de Compras'''
        data_air = []
        temp = {}
        withhold = invoice.withhold_id
        if withhold:
            for line in withhold.line_tax_withhold:
                if line.tipo_retencion == 'renta':
                    if not temp.get(line.retencion.code_name):
                        temp[line.retencion.code_name] = {
                            'baseImpAir': 0,
                            'valRetAir': 0
                        }
                    temp[line.retencion.code_name]['baseImpAir'] += line.base_imponible
                    temp[line.retencion.code_name]['codRetAir'] = line.retencion.code_name
                    temp[line.retencion.code_name]['porcentajeAir'] = int(line.retencion.amount)
                    temp[line.retencion.code_name]['valRetAir'] += abs(line.monto)
        for k, v in temp.items():
            data_air.append(v)
        return data_air

    def get_withholding(self, wh):
        '''Obtenemos la Retención de la Factura'''
        autorizacion = self.env['autorizacion.sri'].search([('tipo_comprobante', '=', 1), ('state', '=', 'activo')])
        return {
            'estabRetencion1': wh.name_retencion[:3],
            'ptoEmiRetencion1': wh.name_retencion[4:7],
            'secRetencion1': str(wh.name_retencion[8:]).lstrip('0'), # Evitar errores
            'autRetencion1': autorizacion.numero_autorizacion,
            'fechaEmiRet1': self.convertir_fecha(wh.fecha)
        }

    def _get_refund(self, invoice):
        """
        Obtenemos la nota de crédito de la factura
        :param invoice:
        :return:
        """
        return {
            'docModificado': '01',
            'estabModificado': invoice.numero_establecimiento,
            'ptoEmiModificado': invoice.punto_emision,
            'secModificado': invoice.numero_factura,
            'autModificado': invoice.numero_autorizacion
        }

    def read_compras(self, period, pay_limit):
        inv_obj = self.env['account.invoice']
        dmn_purchase = [
            ('state', 'in', ['open', 'paid']),
            ('date_invoice', '>=', period.fecha_inicio),
            ('date_invoice', '<=', period.fecha_cierre),
            ('type', 'in', ['in_invoice', 'in_refund', 'in_sale_note'])
        ]
        compras_sistema = inv_obj.search(dmn_purchase)
        compras = []
        for inv in compras_sistema:
            if not inv.partner_id.tipo_de_identificacion == '06':  # Proveedores con pasaporte no se procesa
                if inv.type == 'in_invoice':
                    code = '01'
                elif inv.type == 'in_sale_note':
                    code = '02'
                else:
                    code = '04'
                detallecompras = {}
                valRetBien10, valRetServ20, valorRetBienes, valorRetServicios, valRetServ100 = self._get_ret_iva(
                    inv)
                detallecompras.update({
                    'codSustento': inv.sustento_tributario.codigo,
                    'tpIdProv': tpIdProv[inv.partner_id.tipo_de_identificacion],
                    'idProv': inv.partner_id.vat_eliterp,
                    'tipoComprobante': code,
                    'parteRel': 'NO',
                    'fechaRegistro': self.convertir_fecha(inv.date_invoice),
                    'establecimiento': inv.numero_establecimiento,
                    'puntoEmision': inv.punto_emision,
                    'secuencial': inv.numero_factura,
                    'fechaEmision': self.convertir_fecha(inv.date_invoice),
                    'autorizacion': inv.numero_autorizacion,
                    'baseNoGraIva': '0.00',
                    'baseImponible': '0.00',
                    'baseImpGrav': '%.2f' % inv.amount_untaxed,
                    'baseImpExe': '0.00',
                    'montoIce': '0.00',
                    'montoIva': '%.2f' % inv.amount_tax,
                    'valRetBien10': '0.00',
                    'valRetServ20': '0.00',
                    'valorRetBienes': '%.2f' % valorRetBienes,
                    'valRetServ50': '0.00',
                    'valorRetServicios': '%.2f' % valorRetServicios,
                    'valRetServ100': '%.2f' % valRetServ100,
                    'totbasesImpReemb': '0.00',
                    'detalleAir': self.process_lines(inv)
                })
                detallecompras.update({'pay': True})
                detallecompras.update({'formaPago': inv.payment_metod_ec.code})
                if inv.have_withhold:  # Retención
                    if inv.withhold_id.if_secuencial:
                        detallecompras.update({'retencion': True})
                        detallecompras.update(self.get_withholding(inv.withhold_id))
                if inv.type in ['out_refund', 'in_refund']:
                    if inv.invoice_id_ref:
                        detallecompras.update({'es_nc': True})
                        detallecompras.update(self._get_refund(inv.invoice_id_ref))
                compras.append(detallecompras)
        return compras

    def get_retention_iva(self, retention):
        '''Obtenemos total de líneas de retención tipo IVA'''
        total = 0.00
        for line in retention.line_tax_withhold:
            if line.tipo_retencion == 'iva':
                total += line.monto
        return total

    def get_retention_renta(self, retention):
        '''Obtenemos total de líneas de retención tipo Renta'''
        total = 0.00
        for line in retention.line_tax_withhold:
            if line.tipo_retencion == 'renta':
                total += line.monto
        return total

    @api.multi
    def read_ventas(self, period):
        dmn = [
            ('state', 'in', ('open', 'paid')),
            ('date_invoice', '>=', period.fecha_inicio),
            ('date_invoice', '<=', period.fecha_cierre),
            ('type', '=', 'out_invoice')
        ]
        ventas = []
        for inv in self.env['account.invoice'].search(dmn):
            detalleventas = {
                'tpIdCliente': inv.partner_id.tipo_de_identificacion,
                'idCliente': inv.partner_id.vat_eliterp,
                'parteRel': 'NO',
                'tipoComprobante': inv.autorizacion_sri.tipo_comprobante.code,
                'tipoEm': 'F',
                'numeroComprobantes': 1,
                'baseNoGraIva': 0.00,
                'baseImponible': inv.base_cero_iva,
                'baseImpGrav': inv.base_gravada,
                'montoIva': inv.amount_tax,
                'montoIce': '0.00',
                'valorRetIva': self.get_retention_iva(inv.withhold_id) if inv.withhold_id else 0.00,
                'valorRetRenta': self.get_retention_renta(inv.withhold_id) if inv.withhold_id else 0.00
            }
            ventas.append(detalleventas)
        ventas = sorted(ventas, key=itemgetter('idCliente'))
        ventas_end = []
        for ruc, grupo in groupby(ventas, key=itemgetter('idCliente')):
            baseimp = 0.00
            nograviva = 0.00
            montoiva = 0.00
            retiva = 0.00
            impgrav = 0.00
            retrenta = 0.00
            numComp = 0
            for i in grupo:
                nograviva += i['baseNoGraIva']
                baseimp += i['baseImponible']
                impgrav += i['baseImpGrav']
                montoiva += i['montoIva']
                retiva += i['valorRetIva']
                retrenta += i['valorRetRenta']
                numComp += 1
            detalle = {
                'tpIdCliente': inv.partner_id.tipo_de_identificacion,
                'idCliente': ruc,
                'parteRel': 'NO',
                'tipoComprobante': inv.autorizacion_sri.tipo_comprobante.code,
                'tipoEm': 'F',
                'numeroComprobantes': numComp,
                'baseNoGraIva': '%.2f' % nograviva,
                'baseImponible': '%.2f' % baseimp,
                'baseImpGrav': '%.2f' % impgrav,
                'montoIva': '%.2f' % montoiva,
                'montoIce': '0.00',
                'valorRetIva': '%.2f' % retiva,
                'valorRetRenta': '%.2f' % retrenta,
                'formaPago': '20'
            }
            ventas_end.append(detalle)
        return ventas_end

    @api.multi
    def read_anulados(self, period):
        dmn = [
            ('state', '=', 'cancel'),
            ('date_invoice', '>=', period.fecha_inicio),
            ('date_invoice', '<=', period.fecha_cierre),
            ('type', '=', 'out_invoice')
        ]
        anulados = []
        for inv in self.env['account.invoice'].search(dmn):
            auth = inv.autorizacion_sri
            sec = str(inv.numero_factura[8:]).lstrip('0') # Evitar errores
            detalleanulados = {
                'tipoComprobante': auth.tipo_comprobante.code,
                'establecimiento': auth.numero_establecimiento,
                'puntoEmision': auth.punto_emision,
                'secuencialInicio': sec,
                'secuencialFin': sec,
                'autorizacion': auth.numero_autorizacion
            }
            anulados.append(detalleanulados)
        dmn_ret = [
            ('state', '=', 'cancel'),
            ('fecha', '>=', period.fecha_inicio),
            ('fecha', '<=', period.fecha_cierre),
            ('type', '=', 'purchase'),
            ('if_secuencial', '=', True)
        ]
        for ret in self.env['tax.withhold'].search(dmn_ret):
            auth = self.env['autorizacion.sri'].search([('tipo_comprobante', '=', 1), ('state', '=', 'activo')])
            detalleanulados = {
                'tipoComprobante': auth.tipo_comprobante.code,
                'establecimiento': auth.numero_establecimiento,
                'puntoEmision': auth.punto_emision,
                'secuencialInicio': ret.name_retencion[8:],
                'secuencialFin': ret.name_retencion[8:],
                'autorizacion': auth.numero_autorizacion
            }
            anulados.append(detalleanulados)
        return anulados

    @api.multi
    def render_xml(self, ats):
        """Generar archivo .xml de templates"""
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(tmpl_path))
        ats_tmpl = env.get_template('ats.xml')
        return ats_tmpl.render(ats)

    @api.multi
    def validate_document(self, ats, error_log=False):
        """Validar documento con plantilla .xsd"""
        file_path = os.path.join(os.path.dirname(__file__), 'XSD/ats.xsd')
        schema_file = open(file_path)
        xmlschema_doc = etree.parse(schema_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        utf8_parser = etree.XMLParser(encoding='utf-8')
        root = etree.fromstring(ats.encode('utf-8'), parser=utf8_parser)
        ok = True
        if not self.no_validate:
            try:
                xmlschema.assertValid(root)
            except DocumentInvalid:
                ok = False
        return ok, xmlschema

    @api.multi
    def report_ats(self):
        ats = AccountAts()
        # Información
        period = self.period_id
        ats.TipoIDInformante = 'R'
        ats.IdInformante = self.company_id.partner_id.vat_eliterp
        ats.razonSocial = self.company_id.name.replace('.', '')
        ats.Anio = self.get_date_value(period.fecha_inicio, '%Y')
        ats.Mes = self.get_date_value(period.fecha_inicio, '%m')
        ats.numEstabRuc = self.num_estab_ruc.zfill(3)
        ats.totalVentas = '%.2f' % self._get_ventas(period)
        ats.codigoOperativo = 'IVA'
        # Compras
        ats.compras = self.read_compras(period, self.pay_limit)
        # Ventas
        ats.ventas = self.read_ventas(period)
        # Ventas Establecimiento
        ats.codEstab = '001'
        ats.ventasEstab = '%.2f' % self._get_ventas(period)
        ats.ivaComp = '0.00'
        # Anulados
        ats.anulados = self.read_anulados(period)
        # Proceso del archivo a exportar
        ats_rendered = self.render_xml(ats)
        ok, schema = self.validate_document(ats_rendered)
        buf = StringIO.StringIO()
        buf.write(ats_rendered)
        out = base64.encodestring(buf.getvalue())
        buf.close()
        buf_erro = StringIO.StringIO()
        buf_erro.write(schema.error_log)
        out_erro = base64.encodestring(buf_erro.getvalue())
        buf_erro.close()
        name = "%s-%s%s.xml" % (
            "ATS",
            period.fecha_inicio[5:7],
            period.fecha_inicio[:4]
        )
        data2save = {
            'state': ok and 'export' or 'export_error',
            'data': out,
            'fcname': name
        }
        if not ok:
            data2save.update({
                'state': 'export_error',
                'error_data': out_erro,
                'fcname_errores': 'Error.txt'
            })
        self.write(data2save)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eliterp.reporte.ats',
            'view_mode': ' form',
            'view_type': ' form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    fcname = fields.Char('Nombre de Archivo', size=50, readonly=True)
    fcname_errores = fields.Char('Nombre del Archivo de Error', size=50, readonly=True)
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
    data = fields.Binary('Archivo XML')
    error_data = fields.Binary('Archivo de Error')
    no_validate = fields.Boolean('No Validar', help="Permite valida XML con esquema XSD")
    state = fields.Selection(
        (
            ('choose', 'Elegir'),
            ('export', 'Generado'),
            ('export_error', 'Error')
        ),
        string='Estado',
        default='choose'
    )
