# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2016 Ing. Harry Alvarez, Elitum Group                   #
#                                                                       #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program.  If not, see <http://www.gnu.org/licenses/>. #
#########################################################################


from collections import defaultdict
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import math

UNIDADES = (
    '', 'Un ', 'Dos ', 'Tres ', 'Cuatro ', 'Cinco ', 'Seis ', 'Siete ', 'Ocho ', 'Nueve ', 'Diez ', 'Once ',
    'Doce ',
    'Trece ', 'Catorce ', 'Quince ', 'Dieciseis ', 'Diecisiete ', 'Dieciocho ', 'Diecinueve ', 'Veinte ')
DECENAS = ('Veinti', 'Treinta ', 'Cuarenta ', 'Cincuenta ', 'Sesenta ', 'Setenta ', 'Ochenta ', 'Noventa ', 'Cien ')
CENTENAS = (
    'Ciento ', 'Doscientos ', 'Trescientos ', 'Cuatrocientos ', 'Quinientos ', 'Seiscientos ', 'Setecientos ',
    'Ochocientos ', 'Novecientos ')

MESSAGES = {
    'todos': 'Todos',
    'proveedor': 'Proveedor',
    'cuenta': 'Cuenta'
}

class ReporteComparativoCotizacionesCompras(models.AbstractModel):
    _name = 'report.elitum_compras.reporte_comparativo_cotizaciones_compras'

    def get_proveedor(self, object, numero):
        presupuestos = self.env['purchase.order'].search([('requisition_id', '=', object.id),('selecionar_comparativo','=',True)])
        if (len(presupuestos)>numero)==False:
            return '---------'
        return presupuestos[numero].partner_id.name[:20]

    def get_subtotal_p(self, object, numero):
        presupuestos = self.env['purchase.order'].search([('requisition_id', '=', object.id),('selecionar_comparativo','=',True)])
        if (len(presupuestos) > numero) == False:
            return False
        return presupuestos[numero].amount_untaxed

    def get_impuesto_p(self, object, numero):
        presupuestos = self.env['purchase.order'].search([('requisition_id', '=', object.id),('selecionar_comparativo','=',True)])
        if (len(presupuestos) > numero) == False:
            return False
        return presupuestos[numero].amount_tax

    def get_total_p(self, object, numero):
        presupuestos = self.env['purchase.order'].search([('requisition_id', '=', object.id),('selecionar_comparativo','=',True)])
        if (len(presupuestos) > numero) == False:
            return False
        return presupuestos[numero].amount_total

    def get_line_comparativas(self, object):
        presupuestos = self.env['purchase.order'].search([('requisition_id','=',object.id),('selecionar_comparativo','=',True)])
        lineas_comparativas=[]
        for numero in range(0, len(object.line_ids)):
            lineas_comparativas.append({
                'cantidad':object.line_ids[numero].product_qty,
                'u_medida':object.line_ids[numero].product_uom_id.name,
                'producto':object.line_ids[numero].product_id.name,
                'v_unitario1':presupuestos[0].order_line[numero].price_unit if (len(presupuestos)>0)==True else False,
                'total_1':presupuestos[0].order_line[numero].price_unit if (len(presupuestos)>0)==True else False,
                'v_unitario2':presupuestos[1].order_line[numero].price_unit if (len(presupuestos)>1)==True else False,
                'total_2':presupuestos[1].order_line[numero].price_unit if (len(presupuestos)>1)==True else False,
                'v_unitario3':presupuestos[2].order_line[numero].price_unit if (len(presupuestos)>2)==True else False,
                'total_3':presupuestos[2].order_line[numero].price_unit if (len(presupuestos)>2)==True else False,
            })
        return lineas_comparativas

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'purchase.requisition',
            'docs': self.env['purchase.requisition'].browse(docids),
            'data': data,
            'get_line_comparativas': self.get_line_comparativas,
            'get_proveedor':self.get_proveedor,
            'get_subtotal_p': self.get_subtotal_p,
            'get_impuesto_p': self.get_impuesto_p,
            'get_total_p': self.get_total_p,
        }
        return self.env['report'].render('elitum_compras.reporte_comparativo_cotizaciones_compras', docargs)

# MARZ
class ReporteSolicitudProvision(models.AbstractModel):
    _name = 'report.elitum_compras.reporte_solicitud_provision'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'eliterp.provision',
            'docs': self.env['eliterp.provision'].browse(docids),
            'data': data,
        }
        return self.env['report'].render('elitum_compras.reporte_solicitud_provision', docargs)

class ReporteProvisionLiquidate(models.AbstractModel):
    _name = 'report.elitum_compras.reporte_provision_liquidate'

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'eliterp.provision.liquidate',
            'docs': self.env['eliterp.provision.liquidate'].browse(docids),
            'data': data,
        }
        return self.env['report'].render('elitum_compras.reporte_provision_liquidate', docargs)

class ReporteComprasPdf(models.AbstractModel):
    _name = 'report.elitum_compras.reporte_compras_pdf'

    def get_tipo(self, tipo):
        return MESSAGES.get(tipo)

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'elitumgroup.report.purchases',
            'docs': self.env['elitumgroup.report.purchases'].browse(docids),
            'data': data,
            'get_tipo': self.get_tipo,
            'get_lines': self.env['elitumgroup.report.purchases'].get_lines,
        }
        return self.env['report'].render('elitum_compras.reporte_compras_pdf', docargs)

class ReporteTipoCompraPdf(models.AbstractModel):
    _name = 'report.elitum_compras.reporte_tipo_compra_pdf'

    def get_tipo(self, tipo):
        return MESSAGES.get(tipo)

    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': docids,
            'doc_model': 'elitumgroup.report.purchase.type',
            'docs': self.env['elitumgroup.report.purchase.type'].browse(docids),
            'data': data,
            'get_tipo': self.get_tipo,
            'get_lines': self.env['elitumgroup.report.purchase.type'].get_lines,
        }
        return self.env['report'].render('elitum_compras.reporte_tipo_compra_pdf', docargs)
