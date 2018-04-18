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
from odoo.exceptions import UserError


class purchase_requisition(models.Model):
    _inherit = "purchase.requisition"

    @api.multi
    def action_in_progress(self):
        '''Acción de botón Confirmar'''
        if not all(obj.line_ids for obj in self):
            raise UserError(_('No puede confirmar porqué no hay Líneas de Productos'))
        new_name = self.env['ir.sequence'].next_by_code('purchase.requisition.eliterp')
        self.write({
            'state': 'in_progress',
            'name': new_name
        })

    @api.multi
    def action_open(self):
        # Validar qué se seleccione un presupuesto
        contador = 0
        for line in self.lineas_presupuestos:
            if line['selecionar_presupuesto']:
                contador += 1
        if contador != 1:
            raise UserError(_("Debe seleccionar solo una Línea de Presupuesto/Cotizaciones"))
        self.write({'state': 'open'})

    # MARZ
    @api.multi
    def action_done(self):
        '''Acción de botón Realizado'''
        for purchase_order in self.mapped('purchase_ids'):
            if purchase_order.selecionar_presupuesto:
                purchase_order.button_confirm() # Confirmamos el Presupuesto seleccionado
            else:
                purchase_order.write({
                    'quitar_confirmar_orden': True
                })
        self.write({'state': 'done'})

    def imprimir_solicitud_compra(self):
        '''Imprimimos Solicitud'''
        return self.env['report'].get_action(self, 'elitum_compras.reporte_solicitud_compra')

    def imprimir_comparativo(self):
        '''Imprimimos Comparativo de Presupuestos'''
        count = 0
        for line in self.lineas_presupuestos:
            if line.selecionar_comparativo:
                count += 1
        if count < 2:
            raise UserError(_('Debe comparar al menos dos Presupuestos (Dar check)'))
        return self.env['report'].get_action(self, 'elitum_compras.reporte_comparativo_cotizaciones_compras')

    partner_id = fields.Many2one('res.partner', string="Cliente",
                                 help="Cliente para el cuál se realizará la futura compra")  # MARZ
    ref_solicitud = fields.Char('Referencia')
    name = fields.Char(string='Nombre', required=False, copy=False, default=None, readonly=True)
    mrp_production_id = fields.Many2one('mrp.production', 'Orden de Producción')
    ordering_date = fields.Date(default=fields.Date.context_today, required=True)
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    # MARZ, ('mrp_production', 'Orden de Producción')
    # Sin uso temporal
    type_requisition = fields.Selection([('internal_use', 'Uso Interno'),
                                         ('stock_warehouse', 'Bodega')], "Tipo de Solicitud",
                                        default='stock_warehouse', required=True)
    stock_warehouse_id = fields.Many2one('stock.warehouse', u'Bodega')
    state = fields.Selection([('draft', 'Draft'),
                              ('in_progress', 'Confirmed'),
                              ('open', 'Presupuesto/Cotización'),
                              ('done', 'Done'),
                              ('cancel', 'Anulada')],
                             'Status', track_visibility='onchange', required=True,
                             copy=False, default='draft')
    lineas_presupuestos = fields.One2many('purchase.order', 'requisition_id', u'Línea de Presupuestos')


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    description = fields.Char('Descripción')

    # MARZ
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id # ?
            self.product_qty = 1.0
            self.description = self.product_id.description # Nuevo en método
        if not self.account_analytic_id:
            self.account_analytic_id = self.requisition_id.account_analytic_id
        if not self.schedule_date:
            self.schedule_date = self.requisition_id.schedule_date
