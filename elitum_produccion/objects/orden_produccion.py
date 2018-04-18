# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2016 Ing. Harry Alvarez, Elitum Group                   #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################


from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.exceptions import UserError,except_orm




class EliterpProductionLine(models.Model):

    _name = 'eliterp.production.line'

    name = fields.Char('Descripcion')
    product_id = fields.Many2one('product.template','Producto')
    product_qty = fields.Float('Cantidad')
    product_uom_id = fields.Many2one('product.uom', string='Unidad de Medida')
    state= fields.Selection([('draft', 'Nuevo'),
                             ('fabricando','Fabricando'),
                             ('inventaro','Inventario'),
                             ('compras', 'Compras'),], string='Estado', default='draft')
    production_id = fields.Many2one('mrp.production')


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=False)



# class MrpProductProduce(models.TransientModel):
#     _inherit = "mrp.product.produce"
#
#     @api.multi
#     def do_produce(self):
#         # Nothing to do for lots since values are created using default data (stock.move.lots)
#         moves = self.production_id.move_raw_ids
#         quantity = self.product_qty
#         if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
#             raise UserError(_('You should at least produce some quantity'))
#         for move in moves.filtered(lambda x: x.product_id.tracking == 'none' and x.state not in ('done', 'cancel')):
#             if move.unit_factor:
#                 move.quantity_done_store += quantity * move.unit_factor
#         moves = self.production_id.move_finished_ids.filtered(
#             lambda x: x.product_id.tracking == 'none' and x.state not in ('done', 'cancel'))
#         for move in moves:
#             if move.product_id.id == self.production_id.product_id.id:
#                 move.quantity_done_store += quantity
#             elif move.unit_factor:
#                 move.quantity_done_store += quantity * move.unit_factor
#         self.check_finished_move_lots()
#         if self.production_id.state == 'confirmed':
#             self.production_id.state = 'progress'
#         return {'type': 'ir.actions.act_window_close'}


class StockMove(models.Model):

    _inherit = 'stock.move'

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[], index=True, required=True,
        states={'done': [('readonly', True)]})


class MrpProduction(models.Model):

    _inherit = 'mrp.production'


    def imprimir_orden_produccion(self):
        return self.env['report'].get_action(self, 'elitum_produccion.reporte_orden_produccion')


    @api.multi
    def confirm_mrp_production(self):
        if len(self.routing_id)==0:
            raise except_orm("Error", "Se necesita una ruta de producción")
        # for production in self:
        #     production._generate_finished_moves()
        #     factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id) / production.bom_id.product_qty
        #     boms, lines = production.bom_id.explode(production.product_id, factor, picking_type=production.bom_id.picking_type_id)
        #     production._generate_raw_moves(lines)
        #     # Check for all draft moves whether they are mto or not
        #     self._adjust_procure_method()
        #     self.move_raw_ids.action_confirm()
        return True


    @api.multi
    def _generate_moves(self):
        # for production in self:
        #     production._generate_finished_moves()
        #     factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id) / production.bom_id.product_qty
        #     boms, lines = production.bom_id.explode(production.product_id, factor, picking_type=production.bom_id.picking_type_id)
        #     production._generate_raw_moves(lines)
        #     # Check for all draft moves whether they are mto or not
        #     self._adjust_procure_method()
        #     self.move_raw_ids.action_confirm()
        return True

    @api.multi
    def open_produce_product(self):
        # self.ensure_one()
        # action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
        self.env['mrp.product.produce'].do_produce
        return

    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search([('name', '=', 'Orden de Produccion')])[0].id


    @api.model
    def create(self, vals):
        res = super(MrpProduction, self).create(vals)
        res.update({'name':res.journal_id.sequence_id.next_by_id()})
        return res

    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    pedido_venta_id = fields.Many2one('sale.order',string='Pedido de Venta')
    lines_product_done = fields.One2many('eliterp.production.line', 'production_id', string='Productos a Fabricar')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    notas = fields.Text('Notas', default="prueba")
    product_id = fields.Many2one('product.product', readonly=False, required=False)
    product_uom_id = fields.Many2one('product.uom', 'Medida', readonly=False, required=False)
    product_qty = fields.Float('Quantity To Produce',default=1.0, digits=None,readonly=False, required=False)
    state = fields.Selection([
        ('draft', 'Emitida'),
        ('confirmed', 'Confirmed'),
        ('planned', 'Planned'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State',
        copy=False, default='draft', track_visibility='onchange')

    adjunto = fields.Binary('Adjunto')

    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)

    notas = fields.Text('Notas')

    



