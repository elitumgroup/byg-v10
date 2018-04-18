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
from odoo.tools.misc import formatLang


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    descuento = fields.Float('Descuento')


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # Cambiamos la presentación del nombre del registro
    @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for po in self:
            name = po.name
            if po.amount_total:
                name += ': ' + formatLang(self.env, po.amount_total, currency_obj=po.currency_id)
            result.append((po.id, name))
        return result

    @api.model
    def create(self, vals):
        # Código personalizado
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.customize') or '/'
        # TODO, Cambiamos bodega, de la SC esto lo hacemos para crear varias bodegas
        type_object = self.env['stock.picking.type']
        requisition_id = self.env['purchase.requisition'].browse(self._context['active_id'])
        if requisition_id:
            bodega = requisition_id.stock_warehouse_id.id
        type = type_object.search([('code', '=', 'incoming'), ('warehouse_id', '=', bodega)])
        vals['picking_type_id'] = type.id
        return super(PurchaseOrder, self).create(vals)

    def enviar_solicitud_compra(self):
        '''Enviar SDC/OC por correo electrónico a proveedor'''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = \
                ir_model_data.get_object_reference('elitum_compras', 'template_eliterp_solicitud_presupuesto')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def imprimir_orden_compra(self):
        '''Imprimimos Orden de Compra'''
        return self.env['report'].get_action(self, 'elitum_compras.reporte_orden_compra')

    # MARZ
    @api.multi
    def action_view_picking(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]

        # Cambiamos el contexto, para decirle qué es ingresos a bodega
        result['context'] = {
            'default_tipo_operacion': 'ingreso'
        }
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

    # Cambiamos para bodega de Solicitud de Compra
    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    date_planned = fields.Datetime("Fecha Programada", required=False)
    name = fields.Char('Order Reference', required=False, index=True, copy=False, default=False)  # MARZ
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos',
                                          related='requisition_id.account_analytic_id', store=True)
    project_id = fields.Many2one('eliterp.project', 'Proyecto', related='requisition_id.project_id', store=True)
    selecionar_comparativo = fields.Boolean('Comparativo?')
    # MARZ
    selecionar_presupuesto = fields.Boolean('Seleccionar?')
    state = fields.Selection([
        ('draft', 'Petición de Presupuesto'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'Solicitar Aprobación'),
        ('purchase', 'Orden de Compra'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    quitar_confirmar_orden = fields.Boolean(default=False)  # Ocultar botón Confirmar Orden
    invoice_status = fields.Selection([
        ('no', 'Nada a Facturar'),
        ('to invoice', 'Por Facturar'),
        ('invoiced', 'Facturado'),
    ], string='Estado de Factura', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', states=READONLY_STATES, required=True,
        help="This will determine picking type of incoming shipment")