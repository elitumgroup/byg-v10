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

class eliterp_type_activity(models.Model):

    _name = 'eliterp.type.activity'
    _description = "Tipo de Actividad"

    name=fields.Char('Nombre')
    description = fields.Char('Descripcion')



class contact_crm_activity(models.Model):

    _name = 'contact.crm.activity'

    _description = "Contacto de Actividad"

    name=fields.Char('Nombre')
    address=fields.Char(u'Direccion')
    state_id=fields.Many2one('res.country.state', 'Provincia')
    city=fields.Char(u'Ciudad')
    company=fields.Char(u'Empresa')
    mobile=fields.Char(u'Telefono')
    email=fields.Char(u'Correo')
    referred=fields.Char('Referido por')


class eliterp_sales_management(models.Model):

    _name = 'eliterp.sales.management'

    _description = "Gestion"



    @api.one
    def procesar_requerimiento(self):
        if self.type_activity_id.name != "Cotizar":
            self.write({'state':'done'})

    @api.model
    def create(self, vals):
        vals.update({'date_start':vals['date_activity'],'date_stop':vals['date_activity']})
        return super(eliterp_sales_management, self).create(vals)

    def new_sale_order(self):
        records = self
        context = dict(self._context or {})
        context.update({'from_activity':True,'activity_id':records.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'view_type': 'form',
            'context': context,
        }

    def change_type(self, type):
        crm_type_obj = self.env['eliterp.type.activity'].browse(type)
        token=False
        if crm_type_obj.name=="Cotizar":
            token=True
        return {'value': {'if_sale_order':token}}

    def change_contact_crm(self, contact_crm):
        contact_crm_obj = self.env['contact.crm.activity'].browse(contact_crm)
        return {'value': {'street': contact_crm_obj.address,
                          'city': contact_crm_obj.city,
                          'state_id': contact_crm_obj.state_id.id,
                          'referred': contact_crm_obj.referred,
                          'contact_name': contact_crm_obj.company,
                          'mobile': contact_crm_obj.mobile,
                          'email': contact_crm_obj.email,},}

    def change_client_crm(self, customer):
        client_crm_obj = self.env['res.partner'].browse(customer)
        return {'value': {'street': client_crm_obj.street,
                          'city': client_crm_obj.city,
                          'state_id': client_crm_obj.state_id.id,
                          'mobile': client_crm_obj.mobile,
                          'email': client_crm_obj.email,},}

    name=fields.Char()
    state=fields.Selection([('open','Abierto'),('approval','Esperando Aprobacion'),('done','Realizado')], 'Estado', default='open')
    type_contact= fields.Selection([('customer', 'Cliente'), ('contact', 'Prospecto')],'Tipo', default='customer')
    create_date= fields.Datetime('Fecha Creacion', readonly=True)
    date_activity= fields.Datetime('Fecha')
    contact_crm= fields.Many2one('contact.crm.activity', 'Contacto')
    customer_id= fields.Many2one('res.partner', 'Cliente')
    state_id= fields.Many2one('res.country.state', 'Provincia')
    description= fields.Char('Nota')
    if_sale_order= fields.Boolean('Cotizar', default=False)
    date_action= fields.Datetime('Fecha de Registro')
    mobile=fields.Char('Telef. Celular')
    street=fields.Char('Direccion')
    street=fields.Char('Direccion')
    email=fields.Char('Correo')
    referred=fields.Char('Referido Por')
    city = fields.Char()
    type_activity_id = fields.Many2one('eliterp.type.activity', string='Tipo')
    user_id = fields.Many2one('res.users', 'Vendedor')
    user_id= fields.Many2one('res.users', 'Vendedor')
    date_start= fields.Datetime('Fecha Inicio')
    date_stop= fields.Datetime('Fecha Fin')