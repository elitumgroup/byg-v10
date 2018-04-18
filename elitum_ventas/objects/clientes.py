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


class ClasificacionCliente(models.Model):
    _name = 'clasificacion.cliente'

    _description = u'Clasifación de Cliente'

    name = fields.Char('Nombre')


class ParroquiasDinardap(models.Model):
    _name = 'parroquias.dinardap'

    _description = 'Parroquia'

    name = fields.Char('Parroquia')
    code = fields.Integer(u'Código')
    canton = fields.Many2one('canton.dinardap', string=u'Cantón')


class CantonDinardap(models.Model):
    _name = 'canton.dinardap'

    _description = u'Cantón'

    name = fields.Char(u'Cantón')
    code = fields.Integer(u'Código')
    provincia = fields.Many2one('res.country.state', string='Provincia')


class res_partner(models.Model):
    # MARZ
    def _compute_sale_order_count(self):
        SaleOrder = self.env['sale.order']
        for partner in self:
            partner.sale_order_count = SaleOrder.search_count([
                ('partner_id', 'child_of', partner.id),
                ('type_eliterp', '=', 'pedido_venta')
            ])

    def _compute_presupuestos_count(self):
        SaleOrder = self.env['sale.order']
        for partner in self:
            partner.cotizacion_count = len(SaleOrder.search([
                ('partner_id', 'child_of', partner.id),
                ('type_eliterp', '=', 'draft'),
                ('state_cotizacion_eliterp', '=', 'done')
            ]))

    @api.onchange('property_account_receivable_id')
    def onchange_cuenta(self):
        if self.property_account_receivable_id:
            self.property_account_payable_id = self.property_account_receivable_id.id

    def onchange_vat_eliterp(self, cedula):
        cedula_odoo = ""
        res = {}
        if cedula:
            cedula_odoo = "EC" + cedula
        res = {'value': {'vat': cedula_odoo}}
        return res

    @api.multi
    def name_get(self):
        res = []
        for partner in self:
            name = partner.name or ''
            if self._context.get('show_address_only'):
                name = partner._display_address(without_company=True)
            if self._context.get('show_address'):
                name = name + "\n" + partner._display_address(without_company=True)
            name = name.replace('\n\n', '\n')
            name = name.replace('\n\n', '\n')
            if self._context.get('show_email') and partner.email:
                name = "%s <%s>" % (name, partner.email)
            if self._context.get('html_format'):
                name = name.replace('\n', '<br/>')
            res.append((partner.id, name))
        return res

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        if 'if_freelance_sale' in context:
            vals.update({'if_freelance': True})
        if 'parent_id' in vals:
            if vals['parent_id'] != False:
                vals.update({'is_contact': True})
        if 'no_usuarios' in context:
            vals.update({'customer': False, 'supplier': False})
        return super(res_partner, self).create(vals)

    @api.multi
    def _display_address(self, without_company=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format
        # address_format = self.country_id.address_format or \
        #                  "%(street)s\n%(street2)s\n%(city)s %(state_name)s %(zip)s\n%(country_name)s"

        address_format = u"%(street)s\n%(street2)s\n%(city)s %(state_name)s %(zip)s\n%(country_name)s"
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_id.name or '',
            'company_name': self.commercial_company_name or '',
        }
        for field in self._address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args

    # MARZ
    @api.multi
    def action_quotations_eliterp_cliente(self):
        '''Cotizaciones de Cliente (Estado Emitidas)'''
        cotizaciones = self.env['sale.order'].search([
                ('partner_id', '=', self.id),
                ('type_eliterp', '=', 'draft'),
                ('state_cotizacion_eliterp', '!=', 'done')
            ])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('elitum_ventas.action_quotations_eliterp')
        list_view_id = imd.xmlid_to_res_id('sale.sale.view_quotation_tree')
        form_view_id = imd.xmlid_to_res_id('sale.view_order_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'],
                      [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(cotizaciones) > 1:
            result['context'] = {'search_default_partner_id': self.id}
            result['domain'] = "[('id','in',%s)]" % cotizaciones.ids
        elif len(cotizaciones) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = cotizaciones.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    def action_orders_eliterp_cliente(self):
        '''Pedidos de Cliente'''
        pedidos = self.env['sale.order'].search([
            ('partner_id', '=', self.id),
            ('type_eliterp', '=', 'pedido_venta')
        ])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('elitum_ventas.action_orders_eliterp')
        list_view_id = imd.xmlid_to_res_id('sale.view_order_tree')
        form_view_id = imd.xmlid_to_res_id('sale.view_order_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'],
                      [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(pedidos) > 1:
            result['context'] = {'show_sale': True, 'search_default_partner_id': self.id}
            result['domain'] = "[('id','in',%s)]" % pedidos.ids
        elif len(pedidos) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = pedidos.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    _inherit = 'res.partner'

    tipo_cliente = fields.Selection([('elitum', 'Elitum'), ('directo', 'Directo'), ('especial', 'Especial')], 'Tipo')
    clasificacion_cliente = fields.Many2one('clasificacion.cliente', string=u'Clasificación')
    estado_cliente = fields.Selection([('activo', 'Activo'), ('pasivo', 'Pasivo')], 'Estado')
    segmentacion_cliente = fields.Selection([
        ('agentes_publicidad', 'Agentes de Publicidad'),
        ('agroindustrial', 'Agroindustrial'),
        ('automotriz', 'Automotriz'),
        ('autoservicios', 'Autoservicios'),
        ('cadena_comercial', 'Cadena Comercial'),
        ('centro_comercial', 'Centro Comercial'),
        ('consumo_masivo', 'Consumo Masivo'),
        ('construccion', 'Construcción'),
        ('educacion', 'Educación'),
        ('financiero', 'Financiero'),
        ('hoteleria_turismo', 'Hotelería y Turismo'),
        ('industrial', 'Industrial'),
        ('salud', 'Salud'),
        ('sector_publico', 'Sector Público'),
        ('servicios', 'Servicios'),
        ('tecnologia', 'Tecnología'),
        ('tecnologico', 'Tecnológico'),
        ('telecomunicaciones', 'Telecomunicaciones'),
        ('textil', 'Textil')],
        u'Segmentación')

    type = fields.Selection([('contact', 'Contacto'), ('invoice', u'Dirección de Facturación')], 'Tipo')
    type_seller = fields.Selection([('consultant', 'Asesor'), ('freelance', 'FreeLance')], 'Tipo', default='consultant')
    consultant_sale_id = fields.Many2one('hr.employee', 'Asesor')
    freelance_sale_id = fields.Many2one('res.partner', 'Freelance')
    if_freelance = fields.Boolean('Es Freelance')
    is_contact = fields.Boolean('Es Contacto?')
    vat_eliterp = fields.Char(u'Identificación', required=True)
    company_type = fields.Selection(string='Company Type',
                                    selection=[('person', 'Individual'), ('company', 'Company')],
                                    compute='_compute_company_type', readonly=False, default='person')

    cotizacion_count = fields.Integer(compute='_compute_presupuestos_count', string='Cotizaciones')
    tipo_de_identificacion = fields.Selection([('04', 'RUC'),
                                               ('05', u'Cédula'),
                                               ('06', 'Pasaporte'), ], string=u'Tipo de Identifiación')

    parte_relacionada = fields.Selection([('si', 'Si'),
                                          ('no', 'No')], string=u'Parte Relacionada', default='no')
    canton = fields.Many2one('canton.dinardap', string=u'Cantón')

    parroquia = fields.Many2one('parroquias.dinardap', string='Parroquia')
    cupo_credito = fields.Float(u'Cupo de Crédito')
    sexo = fields.Selection([('m', 'Masculino'),
                             ('f', 'Femenino'), ], string=u'Sexo')
    estado_civil = fields.Selection([('s', 'Soltero'),
                                     ('c', 'Casado'),
                                     ('d', 'Divorciado'),
                                     ('u', 'Unión Libre'),
                                     ('v', 'Viudo'), ], string=u'Estado Civil')
    origen_ingreso = fields.Selection([('b', 'Empleado Público'),
                                       ('v', 'Empleado Privado'),
                                       ('i', 'Independiente'),
                                       ('a', 'Ama de casa o estudiante'),
                                       ('r', 'Rentista'),
                                       ('h', 'Jubilado'),
                                       ('m', 'Remesas del exterior'), ], string=u'Origen de Ingreso')
    property_account_receivable_id = fields.Many2one('account.account',
                                                     string='Cuenta a Pagar',
                                                     domain=[('tipo_contable', '=', 'movimiento')])
