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


from odoo.exceptions import except_orm
from odoo import api, fields, models, _


class CodigoProductoEliterp(models.Model):
    _name = 'codigo.producto.eliterp'

    _description = u'Código de Producto'

    @api.one
    def _get_total(self):
        if self.lines_productos_ids:
            numbers = len(self.lines_productos_ids)
            self.cantidad = str(numbers)

    name = fields.Char(u'Código')
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia')
    lines_productos_ids = fields.One2many('product.template', 'codigo_producto_eliterp_id', 'Productos')
    cantidad = fields.Char('Cantidad de Productos', compute='_get_total')  # MARZ


class LineaProductoEliterp(models.Model):
    _name = 'linea.producto.eliterp'

    _description = u'Línea de Producto'

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        if 'default_level_upper' in context:
            if context['default_level_upper'] == False:
                raise except_orm("Error", "No puede crear una Línea de Producto sin escoger una Categoría")
        return super(LineaProductoEliterp, self).create(vals)

    name = fields.Char('Línea')
    level_upper = fields.Many2one('product.category', string=u'Categoría', readonly=True)


class SubLineaProductoELiterp(models.Model):
    _name = 'sub.linea.producto.eliterp'

    _description = u'SubLínea de Producto'

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        if 'default_level_upper' in context:
            if context['default_level_upper'] == False:
                raise except_orm("Error", "No puede crear una SubLínea de Producto sin escoger una Línea")
        return super(SubLineaProductoELiterp, self).create(vals)

    name = fields.Char(u'SubLínea')
    level_upper = fields.Many2one('linea.producto.eliterp', string=u'Línea', readonly=True)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.one
    def _compute_partner_ref(self):
        '''Cambiar nombre del producto'''
        for supplier_info in self.seller_ids:
            if supplier_info.name.id == self._context.get('partner_id'):
                product_name = supplier_info.product_name or self.default_code
        else:
            product_name = self.name
        self.partner_ref = self.name


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('type')
    def _onchange_type(self):
        self.track_service = 'manual'

    @api.model
    def create(self, vals):
        categ = self.env['product.category'].browse(vals['categ_id']).name
        linea = self.env['linea.producto.eliterp'].browse(vals['linea_producto_id']).name
        sublinea = self.env['sub.linea.producto.eliterp'].browse(vals['sub_linea_producto_id']).name
        code_name = (categ[:3]).upper() + "-" + (linea[:3]).upper() + "-" + (sublinea[:3]).upper()
        codigo_eliterp_id = self.env['codigo.producto.eliterp'].search([('name', '=', code_name)])
        if len(codigo_eliterp_id._ids) != 0:
            code_sequence = (categ[:3]).upper() + "." + (linea[:3]).upper() + "." + (sublinea[:3]).upper()
            obj_sequence = self.env['ir.sequence']
            sequence = obj_sequence.next_by_code(code_sequence)
            vals.update({'default_code': sequence, 'codigo_producto_eliterp_id': codigo_eliterp_id.id})
        else:
            code_sequence = (categ[:3]).upper() + "." + (linea[:3]).upper() + "." + (sublinea[:3]).upper()
            new_sequence_product = self.env['ir.sequence'].create({'name': "Producto " + code_name,
                                                                   'code': code_sequence,
                                                                   'prefix': code_name,
                                                                   'padding': 5
                                                                   })
            new_codigo_eliterp = self.env['codigo.producto.eliterp'].create({'name': code_name,
                                                                             'sequence_id': new_sequence_product.id})
            obj_sequence = self.env['ir.sequence']
            sequence = obj_sequence.next_by_code(code_sequence)
            vals.update({
                'default_code': sequence,
                'codigo_producto_eliterp_id': new_codigo_eliterp.id
            })
        return super(ProductTemplate, self).create(vals)

    def action_view_orderpoints(self):
        rules_id = self.env('stock.warehouse.orderpoint').search([('product_id', '=', self.id)])._ids
        res = {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.warehouse.orderpoint',
            'view_mode': 'form',
            'view_type': 'form',
        }
        if rules_id:
            res['res_id'] = rules_id[0]
            res['context'] = "{}"
        else:
            res['context'] = "{'default_product_id': " + str(self.id) + "}"
        return res

    '''
        No necesarios en ELITUMDEVELOP
        ,('tools', 'Herramientas'), ('product_done', 'Producto Terminado')
    '''
    type = fields.Selection([
        ('product', 'Almacenable'),
        ('consu', 'Consumible'),
        ('service', 'Servicio')
    ], 'Tipo de Producto')
    linea_producto_id = fields.Many2one('linea.producto.eliterp', 'Linea', required=True)
    sub_linea_producto_id = fields.Many2one('sub.linea.producto.eliterp', u'SubLínea', required=True)
    codigo_producto_eliterp_id = fields.Many2one('codigo.producto.eliterp', u'Código Interno')
    can_be_expensed = fields.Boolean(help="Specify whether the product can be selected in an HR expense.",
                                     string="Puede ser tratado como gasto")
    # MARZ
    category_uom_id = fields.Many2one(
        'product.uom.categ', u'Categoría de Medida')
    medida_producto = fields.Char('Medida del Producto')
    presentation = fields.Selection([
        ('none', 'Sin Especificar'),
        ('funda', 'Funda'),
        ('botella', 'Botella')
    ], string=u'Presentación', default='none', required=True)
