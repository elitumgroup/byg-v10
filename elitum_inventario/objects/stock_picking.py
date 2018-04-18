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


from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo import api, fields, models, _


class Picking(models.Model):
    def imprimir_control_inventario(self):
        '''Imprimir reporte de Control de Inventario'''
        if self.tipo_operacion == 'ingreso':
            return self.env['report'].get_action(self, 'elitum_inventario.reporte_ingreso_bodega')
        elif self.tipo_operacion == 'egreso':
            return self.env['report'].get_action(self, 'elitum_inventario.reporte_egreso_bodega')
        else:
            return self.env['report'].get_action(self, 'elitum_inventario.reporte_transferencia_bodega')

    '''
    @api.onchange('proveedor_id')
    def onchange_proveedor_id(self):
        if self.proveedor_id:
            self.partner_id = self.proveedor_id
    '''

    @api.onchange('cliente_id')
    def onchange_cliente_id(self):
        if self.cliente_id:
            self.partner_id = self.cliente_id

    _inherit = 'stock.picking'

    proveedor_id = fields.Many2one('res.partner') # ?
    cliente_id = fields.Many2one('res.partner')
    responsable_bodega_id_origin = fields.Many2one('res.users')
    responsable_bodega_id_destino = fields.Many2one('res.users')
    state = fields.Selection([
        ('draft', 'Nuevo'),
        ('cancel', 'Cancelado'),
        ('waiting', 'En Espera'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'En Proceso'), ('done', 'Done')], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n"
             " * Waiting Availability: still waiting for the availability of products\n"
             " * Partially Available: some products are available and reserved\n"
             " * Ready to Transfer: products reserved, simply waiting for confirmation.\n"
             " * Transferred: has been processed, can't be modified or cancelled anymore\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    tipo_operacion = fields.Selection([
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
        ('transferencia', 'Transferencia')
    ], string=u"Tipo de Operación")
