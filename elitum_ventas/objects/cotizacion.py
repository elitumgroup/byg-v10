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



from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError
from odoo import api, fields, models, _
import datetime
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

LINE_NEGATION = {
    'competencia': 'Competencia',
    'precio': 'Precio',
    'demora': 'Demora en Proceso',
    'suspension': 'Suspensión de proyecto',
    'otro': 'Otro'
}


class res_partner(models.Model):
    _inherit = 'res.partner'

    if_freelance = fields.Boolean('FreeLance')


class eliterp_validity(models.Model):
    _name = 'eliterp.validity'

    _description = 'Vigencia Para Cotizacion'

    name = fields.Char('Vigencia', required=True)
    value = fields.Integer(u'Días', required=True)


class eliterp_sale_order_line_partial(models.Model):
    _name = 'eliterp.sale.order.line.partial'

    _description = u'Línea Parcial de Cotizaciones'

    def _get_lines_partial(self):
        context = dict(self._context or {})
        return self.env['sale.order.line'].search([('order_id', '=', context['active_id'])])

    lines_partial = fields.Many2many('sale.order.line',
                                     'sale_order_line_partial_order',
                                     'lines_partial_id',
                                     'sale_order_id',
                                     select=True, string="Lineas", defaul=_get_lines_partial)

    name = fields.Char('nombre')


class denied_sale_order_wizard(models.Model):
    _name = 'denied.sale_order.wizard'

    _description = 'Linea Negada Cotizacion'

    @api.model
    def create(self, vals):
        vals.update({'name': LINE_NEGATION.get(vals['type_denied'], '')})  # MARZ
        id_denied = super(denied_sale_order_wizard, self).create(vals, )
        context = dict(self._context or {})
        if 'linea' in context:
            order_line = self.env['sale.order.line'].browse([context['active_id']])
            order_line.write({'line_approval': 'denied'})
            res = self.env['sale.order.line'].all_lines(order_line.order_id.id)
            if res == 1:
                order_line.order_id.write({'state_cotizacion_eliterp': 'done'})
            else:
                order_line.order_id.write({'state_cotizacion_eliterp': 'sale_partial'})
            order_line.write({'razon_negado': id_denied.id})
        else:
            order = self.env['sale.order'].browse([context['active_id']])
            order.write({'state_cotizacion_eliterp': 'denied'})
            order.write({'razon_negado': id_denied.id})
        return id_denied

    name = fields.Char(u'Razón')
    type_denied = fields.Selection([('competencia', 'Competencia'),
                                    ('precio', 'Precio'),
                                    ('demora', 'Demora en Proceso'),
                                    ('suspension', 'Suspensión de proyecto'),
                                    ('otro', 'Otro')], u'Negado por', required=True)
    notas = fields.Text(u'Descripción')


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    def all_lines(self, order_id):
        '''Líneas de Cotización'''
        lines = self.env['sale.order.line'].search([('order_id', '=', order_id)])._ids
        lines_objs = self.env['sale.order.line'].browse(lines)
        count = 0
        for l in lines_objs:
            if l.line_approval == 'pending':
                count += 1
        if count == 0:
            return 1
        else:
            return 2

    def line_accepted(self):
        '''Aprobar líneas de pedido'''
        self.write({'line_approval': 'accepted'})
        res = self.all_lines(self.order_id.id)
        self.order_id.write({'can_create_new_sale_order': True})
        # Aprobamos parcial o total
        if res == 1:
            self.order_id.write({'state_cotizacion_eliterp': 'done'})
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            self.order_id.write({'state_cotizacion_eliterp': 'sale_partial'})
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def line_denied(self):
        '''Negamos Línea de Cotización'''
        context = dict(self._context or {})
        context.update({'linea': 1})
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'denied.sale_order.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    line_approval = fields.Selection([('pending', 'Pendiente'),
                                      ('sale_order', 'Pedido de Venta'),
                                      ('accepted', 'Aprobado'),
                                      ('facturado', 'Facturado'),  # MARZ
                                      ('denied', 'Negada')], 'Estado', default='pending')
    razon_negado = fields.Many2one('denied.sale_order.wizard', u'Razón de Negación')
    # MARZ
    facturado = fields.Boolean(default=False, string='Facturar?')


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.multi
    def create_invoices(self):
        invoices = super(SaleAdvancePaymentInv, self).create_invoices()
        order = self.env['sale.order'].browse(self._context['active_id'])
        order.write({'state_pedido_eliterp': 'invoice', 'have_factura': True})
        if order.have_orden_produccion == True:
            order.write({'state_pedido_eliterp': 'done'})
        return invoices


class SaleOrder(models.Model):

    @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('elitum_ventas', 'template_eliterp_ventas')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "elitum_ventas.mail_template_data_notification_email_sale_order_eliterp"
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

    @api.multi
    @api.constrains('order_line')
    def _check_multi_timesheet(self):
        return

    def action_view_orden_produccion(self):
        orden_produccion = self.env['mrp.production'].search([('pedido_venta_id', '=', self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('mrp.mrp_production_action')
        list_view_id = imd.xmlid_to_res_id('mrp.mrp_production_tree_view')
        form_view_id = imd.xmlid_to_res_id('mrp.mrp_production_form_view')
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
        if len(orden_produccion) > 1:
            result['domain'] = "[('id','in',%s)]" % orden_produccion.ids
        elif len(orden_produccion) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = orden_produccion.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    def action_view_pedido_ventas(self):
        pedidos = self.env['sale.order'].search([('order_id_eliterp', '=', self.id)])
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
            result['domain'] = "[('id','in',%s)]" % pedidos.ids
        elif len(pedidos) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = pedidos.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    def action_cancel(self):
        '''Anular Cotización/Pedido de Venta'''
        records = self
        lines = self.env['sale.order.line'].search([('order_id', '=', records.id)])
        for line in lines:
            # Verificamos Líneas de Pedido
            if line.line_approval == 'sale_order':
                raise except_orm("Error", "No puede Cancelar, tiene Líneas en Estado Pedido de Venta")
        self.write({
            'state_cotizacion_eliterp': 'cancel',
            'can_create_new_sale_order': False
        })
        return super(SaleOrder, self).action_cancel()

    def action_aprobar(self):
        '''Aprobar Cotización'''
        records = self
        lines = self.env['sale.order.line'].search([('order_id', '=', records.id)])._ids
        if len(lines) == 0:
            raise except_orm("Error", "No hay Líneas de Pedido para Aprobrar")
        for line in lines:
            # Cambiamos estado a Líneas de Cotización
            order_line = self.env['sale.order.line'].browse(line)
            order_line.write({'line_approval': 'accepted'})
        # Retornamos para Crear Pedido de Venta
        return self.write({
            'state_cotizacion_eliterp': 'done',
            'can_create_new_sale_order': True
        })

    def action_negar(self):
        '''Acción negar Línea de Cotización'''
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'denied.sale_order.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    @api.multi
    def action_new_pedido_venta(self):
        '''Creamos Pedido desde la Cotización'''
        records = self
        lines = self.env['sale.order.line'].search([('order_id', '=', records.id)])._ids
        if len(lines) == 0:
            raise Warning("No hay Líneas para crear Pedido de Ventas")
        else:
            lines_id = self.env['sale.order.line'].browse(lines)
            count_pendientes = 0
            count_negadas = 0
            count_aprobadas = 0
            for l in lines_id:
                if l.line_approval == 'pending':
                    count_pendientes += 1
                if l.line_approval == 'denied':
                    count_negadas += 1
                if l.line_approval == 'accepted':
                    count_aprobadas += 1
            # Líneas Pendientes
            if count_pendientes >= 1 and count_aprobadas == 0:
                raise Warning('Hay Líneas de Pedido de Ventas pendientes')
            # Líneas Negadas
            if count_negadas >= 1 and count_aprobadas == 0 and count_pendientes == 0:
                raise Warning("Solo existen Líneas de Pedido negadas")
            # Crear Nuevo Pedido
            new_pedido_venta = self.create({
                'partner_id': records.partner_id.id,
                'date_created': records.date_created,
                'validity_id': records.validity_id.id if records.validity_id else False,
                # MARZ
                'centro_costos': records.centro_costos.id if records.centro_costos else False,
                'proyecto_id': records.proyecto_id.id if records.proyecto_id else False,
                'order_id_eliterp': self.id,
                'type_eliterp': 'pedido_venta',
                'payment_term_id': records.payment_term_id.id if records.payment_term_id else False,
            })
            for l in lines_id:
                if l.line_approval == 'accepted':
                    # Creamos Líneas de Pedido/Pedido de Ventas
                    new_linea_pedido_venta = self.env['sale.order.line'].create({
                        'product_uom_qty': l.product_uom_qty,
                        'product_id': l.product_id.id,
                        'name': l.name,
                        'price_subtotal': l.price_subtotal,
                        'price_unit': l.price_unit,
                        'price_total': l.price_total,
                        'discount': l.discount,
                        'tax_id': [(6, 0, [l.tax_id.id])],
                        'line_approval': 'accepted',
                        'order_id': new_pedido_venta.id,
                    })
                    l.write({'line_approval': 'sale_order'})
            # Crea pedido en estado Emitido"
            new_pedido_venta.action_confirm()
            new_pedido_venta.write({
                'state_pedido_eliterp': 'order',
                'state_cotizacion_eliterp': 'sale_order',
                'type_eliterp': 'pedido_venta'
            })
            res = self.env['sale.order.line'].all_lines(self.id)
            if res == 1:
                self.write({'state_cotizacion_eliterp': 'done'})
            self.write({'can_create_new_sale_order': False})
            self.write({'have_pedidos_ventas': True})
        return True

    def action_new_orden_produccion(self):
        vals = {'pedido_venta_id': self.id}
        produccion_id = self.env['mrp.production'].create(vals)
        lines = self.env['sale.order.line'].search([('order_id', '=', self.id)])
        for l in lines:
            self.env['eliterp.production.line'].create({
                'product_id': l.product_id.id,
                'product_uom_id': l.product_uom.id,
                'product_qty': l.product_uom_qty,
                'state': 'draft',
                'production_id': produccion_id.id
            })
        self.write({'state_pedido_eliterp': 'mrp', 'have_orden_produccion': True})
        if self.have_factura == True:
            self.write({'state_pedido_eliterp': 'done'})
        return

    def _get_pedidos(self):
        '''Obtemos la cantidad de pedidos'''
        pedidos = self.env['sale.order'].search([('order_id_eliterp', '=', self[0].id)])
        self[0].update({'pedidos_count': len(pedidos)})

    def get_moneda(self):
        return self.env['res.currency'].search([('name', '=', 'USD')])[0].id

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        validity_obj = self.env['eliterp.validity'].browse(vals['validity_id'])
        validity_days = datetime.datetime.strptime(vals['date_created'], "%Y-%m-%d") + datetime.timedelta(
            validity_obj.value)
        vals.update({'validity_date': validity_days.strftime("%Y-%m-%d")})
        if 'from_activity' in context:
            sales_management = self.env['eliterp.sales.management'].browse([context['activity_id']])
            sales_management.write({'state': 'done'})
        if 'type_eliterp' in vals:
            if vals['type_eliterp'] == 'draft':
                obj_sequence = self.env['ir.sequence']
                sequence = obj_sequence.next_by_code('sale.order.cotizacion')
                vals.update({'name': sequence})
            else:
                obj_sequence = self.env['ir.sequence']
                sequence = obj_sequence.next_by_code('sale.order.pedido.venta')
                vals.update({'name': sequence})
        return super(SaleOrder, self).create(vals)

    @api.depends('order_line.price_total')
    def _get_total_discount(self):
        if not self.order_line:
            return 0.00
        else:
            total_descuento = 0.00
            for line in self.order_line:
                sub_total = round(line.price_unit * line.product_uom_qty * (line.discount / 100), 2)
                total_descuento += sub_total
            self.update({'total_discount': total_descuento})

    _inherit = 'sale.order'

    name = fields.Char(string='Order Reference', required=False, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=False)
    date_created = fields.Date(u'Fecha de Emisión', default=datetime.datetime.now())
    order_id_eliterp = fields.Many2one('sale.order', u'Cotización')
    razon_negado = fields.Many2one('denied.sale_order.wizard', 'Negado por')
    validity_id = fields.Many2one('eliterp.validity', 'Vigencia')
    state_cotizacion_eliterp = fields.Selection([
        ('draft', 'Emitida'),
        ('sale_partial', 'Parcial'),
        ('denied', 'Negada'),
        ('done', 'Cerrada'),
        ('cancel', 'Anulada'),
        ('sale_order', 'Pedido de Venta'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    state_pedido_eliterp = fields.Selection([
        ('order', 'Emitido'),
        ('mrp', 'En Producción'),
        ('invoice_parcial', 'Facturado Parcial'),  # MARZ
        ('invoice', 'Facturado'),
        ('done', 'Cerrado'),
        ('cancel', 'Anulado'),
    ], string='Status', readonly=True)
    can_create_new_sale_order = fields.Boolean('Puede Crear Pedido de Ventas?', default=False)
    have_pedidos_ventas = fields.Boolean('Tiene Pedido de Ventas?', default=False)
    have_orden_produccion = fields.Boolean('Tiene Orden de Produccion?', default=False)
    have_factura = fields.Boolean('Tiene Factura?', default=False) # ?
    pedidos_count = fields.Integer(string='Pedidos', compute='_get_pedidos', readonly=True)
    contact_id = fields.Many2one('res.partner', 'Contactos')
    account_invoice_id = fields.Many2one('account.invoice', string='Factura') # ?
    currency_id = fields.Many2one('res.currency', default=get_moneda, related=None, readonly=True)
    type_eliterp = fields.Selection([
        ('draft', 'cotizacion'),
        ('pedido_venta', 'pedido_venta'),
    ], u"Tipo Según Eliterp", default='draft')
    descuento_global = fields.Boolean(string=u'Descuento Global', default=False)
    descuento_global_amount = fields.Float(string=u'Descuento')
    base_cero_iva = fields.Float(string=u'Base Cero', readonly=True)
    base_gravada = fields.Float(string=u'Base Iva', readonly=True)
    total_discount = fields.Float(string=u'Descuento', compute='_get_total_discount', readonly=True, store=True)
    consultant_sale_id = fields.Many2one('hr.employee', 'Asesor', related='partner_id.consultant_sale_id', store=True)
    # MARZ (MAEQ)
    proyecto_id = fields.Many2one('eliterp.project', 'Proyecto')
    centro_costos = fields.Many2one('account.analytic.account', 'Centro de Costos')
    notes = fields.Text()
    type_register = fields.Selection([
        ('print', 'Imprimir en Documento'),
        ('interna', 'Conservar como información Interna')
    ], 'Tipo de Registro', default='print', required=True)
    have_anticipo = fields.Boolean('Tiene Anticipo?', default=False)

    @api.depends('amount_total')
    def _get_saldo_pendiente(self):
        self.saldo_pendiente_facturar = 0

    @api.one
    def make_invoice_eliterp(self):
        '''Crear Factura total o parcial'''
        # Verificamos qué exista una línea para facturar
        lines_total_aprobadas = self.order_line.filtered(
            lambda r: r.line_approval == 'accepted' or r.line_approval == 'facturado')
        lines_total = self.order_line.filtered(lambda r: r.line_approval == 'accepted' and r.facturado)
        if len(lines_total) == 0:
            raise Warning("Debe marcar al menos una Línea de Pedido para facturar")
        estado = 'invoice_parcial'
        contador = 0
        for line in lines_total_aprobadas:
            if line.facturado:
                contador += 1
        # Validamos Líneas con Check de Facturar
        if len(lines_total_aprobadas) == contador:
            estado = 'invoice'
        self.with_context(active_model=u'sale.order').action_invoice_create()
        self.write({
            'state_pedido_eliterp': estado
        })

    def aplicar_descuento_global(self):
        '''Aplicar Descuento'''
        if not self.order_line:
            raise Warning("No hay líneas para aplicar descuento")
        else:
            for line in self.order_line:
                line.update({'discount': self.descuento_global_amount})
        return

    def imprimir_cotizacion(self):
        return self.env['report'].get_action(self, 'elitum_ventas.reporte_cotizacion')

    @api.multi
    def write(self, values):
        if 'state' in values:
            if values['state'] == 'sent':
                values.update({'state': self.state})
        return super(SaleOrder, self).write(values)

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()
        if self.partner_id:
            if self.partner_id.consultant_sale_id:
                self.consultant_sale_id = self.partner_id.consultant_sale_id
            else:
                self.consultant_sale_id = False
        return res

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name': self.client_order_ref or '',
            'origin': self.name,
            'date_invoice': self.date_created,
            'type': 'out_invoice',
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'journal_id': journal_id,
            'currency_id': self.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'consultant_sale_id': self.consultant_sale_id.id
        }
        return invoice_vals

    # MARZ
    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        for order in self:
            order_line = order.order_line.filtered(
                lambda a: a.line_approval == 'accepted' and a.facturado)  # Soló líneas aceptadas y check de facturar
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)
            for line in order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                line.write({'line_approval': 'facturado'})  # Le cambiamos estado a Facturado
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.name
                    if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
                        vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                    invoices[group_key].write(vals)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)

            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoice] = references[invoice] | order

        if not invoices:
            raise UserError(_('There is no invoicable line.'))

        for invoice in invoices.values():
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoicable line.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_untaxed < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                                           values={'self': invoice, 'origin': references[invoice]},
                                           subtype_id=self.env.ref('mail.mt_note').id)
        return [inv.id for inv in invoices.values()]

    @api.depends('state', 'order_line.invoice_status')
    def _get_invoiced(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.

        The invoice_ids are obtained thanks to the invoice lines of the SO lines, and we also search
        for possible refunds created directly from existing invoices. This is necessary since such a
        refund is not directly linked to the SO.
        """
        for order in self:
            invoice_ids = order.order_line.mapped('invoice_lines').mapped('invoice_id')
            # Search for invoices which have been 'cancelled' (filter_refund = 'modify' in
            # 'account.invoice.refund')
            # use like as origin may contains multiple references (e.g. 'SO01, SO02')
            refunds = invoice_ids.search([('origin', 'like', order.name)])
            invoice_ids |= refunds.filtered(lambda r: order.name in [origin.strip() for origin in r.origin.split(',')])
            # Buscar pedidos qué tengan anticipos
            anticipos = self.env['account.invoice'].search([('pedido_relacionado', '=', order.id)])
            # Search for refunds as well
            refund_ids = self.env['account.invoice'].browse()
            if invoice_ids:
                for inv in invoice_ids:
                    refund_ids += refund_ids.search(
                        [('type', '=', 'out_refund'), ('origin', '=', inv.number), ('origin', '!=', False),
                         ('journal_id', '=', inv.journal_id.id)])

            line_invoice_status = [line.invoice_status for line in order.order_line]

            if order.state not in ('sale', 'done'):
                invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                invoice_status = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                invoice_status = 'invoiced'
            elif all(invoice_status in ['invoiced', 'upselling'] for invoice_status in line_invoice_status):
                invoice_status = 'upselling'
            else:
                invoice_status = 'no'
            # MARZ
            order.update({
                'invoice_count': len(set(invoice_ids.ids + refund_ids.ids + anticipos.ids)),
                'invoice_ids': invoice_ids.ids + refund_ids.ids + anticipos.ids,
                'invoice_status': invoice_status
            })
