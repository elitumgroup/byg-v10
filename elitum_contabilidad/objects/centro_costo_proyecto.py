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

from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    nombre_centro = fields.Char('Nombre')


class EliterpProject(models.Model):
    _name = 'eliterp.project'

    _description = 'Proyecto'

    name = fields.Char('Nombre de Proyecto', required=True)
    codigo = fields.Char(u'Código', required=True)
    referencia = fields.Char('Referencia')
    account_analytic_id = fields.Many2one('account.analytic.account', string="Centro de Costo", required=True)

    _sql_constraints = [
        ('contabilidad_codigo_unique', 'unique (codigo)', "El Código del proyecto ya existe")
    ]