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


class RiseCategory(models.Model):
    _name = 'rise.category'
    _description = u'Modelo - Categoría RISE'

    @api.multi
    def name_get(self):
        result = []
        for data in self:
            result.append((data.id, "Categoría No. %s" % (data.name)))
        return result

    name = fields.Integer(u'Categoría No.')
    min_amount = fields.Float(u'Mínimo')
    max_amount = fields.Float(u'Máximo')


class RiseActivity(models.Model):
    _name = 'rise.activity'

    _description = 'Modelo - Actividad RISE'

    name = fields.Char('Nombre')


# MARZ
class RiseCategoryActivity(models.Model):
    _name = 'rise.category.activity'
    _description = u'Modelo - Categoría - Actividad RISE'

    @api.multi
    def name_get(self):
        result = []
        for data in self:
            result.append((data.id, u"Categoría No. %s - %s" % (data.category_id.name, data.activity_id.name)))
        return result

    category_id = fields.Many2one('rise.category', u'Categoría')
    activity_id = fields.Many2one('rise.activity', 'Actividad')
    max_amount = fields.Float(u'Monto Máximo (Mensual)')
    status = fields.Boolean('Activo?', default=True)
