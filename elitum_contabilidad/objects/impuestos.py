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


class account_tax_code (models.Model):

    _name='account.tax.code'

    name=fields.Char(u'Código')
    description=fields.Char('Nombre')
    parent_tax_code_id= fields.Many2one('account.tax.code', u'Código Padre')


class account_tax(models.Model):

    _inherit = 'account.tax'

    code_name=fields.Char(u'Código')
    taxable_code_id=fields.Many2one('account.tax.code', u'Código Base Imponible')
    tieback_code_id=fields.Many2one('account.tax.code', u'Código Valor Retenido')
    tipo_impuesto = fields.Selection([
        ('iva','IVA'),('retencion', 'Retención')
    ], string=u'Tipo de Impuesto', default='iva')
    tipo_retencion = fields.Selection([('renta','Renta'),('iva','IVA')],
                                      string=u'Tipo de Retención')
