# -*- encoding: utf-8 -*-
#########################################################################
# Copyright (C) 2018 Ing. Mario Rangel, Elitum Group                   #
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


class StockWarehouse(models.Model):
    _name = 'elitum.lines.responsables.warehouse'
    _description = u'Líneas de Responsables de Bodega'

    stock_warehouse_id = fields.Many2one('stock.warehouse', 'Bodega')
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    departamento = fields.Many2one('hr.department', string='Departamento', related='employee_id.department_id')
    prioridad = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], help='Da un grado de responsabilidad mayor al responsable', string='Prioridad', default='1',
        required=True)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    lines_responsables = fields.One2many('elitum.lines.responsables.warehouse', 'stock_warehouse_id',
                                         u'Líneas de Responsables')

    # Cambiar las secuencias a la creación de bodegas
    def _get_sequence_values(self):
        return {
            'in_type_id': {
                'name': self.name + _(' Secuencia Ingresos'),
                'prefix': self.code + '-ING-%(year)s-%(month)s-',
                'padding': 5
            },
            'out_type_id': {
                'name': self.name + _(' Secuencia Egresos'),
                'prefix': self.code + '-EGR-%(year)s-%(month)s-',
                'padding': 5
            },
            'pack_type_id': {
                'name': self.name + _(' Secuencia Packing'),
                'prefix': self.code + '-PAC-%(year)s-%(month)s-',
                'padding': 5
            },
            'pick_type_id': {
                'name': self.name + _('Secuencia Picking'),
                'prefix': self.code + '-PIC-%(year)s-%(month)s-',
                'padding': 5
            },
            'int_type_id': {
                'name': self.name + _('Secuencia Internos'),
                'prefix': self.code + '-INT-%(year)s-%(month)s-',
                'padding': 5
            },
        }

