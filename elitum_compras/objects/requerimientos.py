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
from odoo.exceptions import UserError, ValidationError
import json
from datetime import datetime


class EliterpRequestProduct(models.Model):
    _name = 'eliterp.request.product'

    _description = "Producto de Requerimiento"

    name = fields.Char('Nombre', required=True)
    description = fields.Char(U'Descripción')


class EliterpRequestTypeProduct(models.Model):
    _name = 'eliterp.request.type.product'

    _description = "Producto para Requerimiento"

    product_requerimiento_id = fields.Many2one('eliterp.request.product', 'Producto', required=True)
    resquest_id = fields.Many2one('eliterp.request', 'Requerimiento')
    qty_product = fields.Integer('Cantidad')


class EliterpRequestType(models.Model):
    _name = 'eliterp.request.type'

    _description = "Tipo Requerimiento"

    name = fields.Char('Nombre', required=True)


class EliterpRequest(models.Model):
    def procesar_requerimiento(self):
        return self.write(
            {'state': 'done', 'state_approved': 'done', 'state_manager': 'done', 'done_date': fields.Datetime.now()})

    def aprobar_requerimiento(self):
        records = self
        return self.write({'state': 'approved', 'state_approved': 'approved', 'state_manager': 'approved_pending'})

    def negar_requerimiento(self):
        records = self
        return self({'state': 'denied', 'state_approved': 'denied', 'state_manager': 'denied'})

    def crear_solicitud_compra(self):
        records = self
        return self.write({'state': 'in_process', 'state_approved': 'in_process', 'state_manager': 'in_process',
                           'done_date': fields.Datetime.now()})

    def get_qty_product(self):
        records = self
        return

    def get_type_user(self):
        records = self
        result = {}
        usuario = False
        if records.create_uid.id == self._uid:
            self.type_user = 'request'
        else:
            if records.user_receiving.id == self._uid:
                self.type_user = 'manager'
            else:
                if records.manager_receiving.id == self._uid:
                    self.type_user = 'approved'

    def solicitar_requerimiento(self):
        records = self
        if records.type_workflow == 'approved':
            return self.write({'state': 'sent', 'state_approved': 'pending', 'state_manager': 'pending'})
        else:
            return self.write({'state': 'sent', 'state_manager': 'approved_pending'})

    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search([('name', '=', 'Requerimientos')])[0].id

    @api.model
    def create(self, vals):
        res = super(EliterpRequest, self).create(vals)
        res.name = res.journal_id.sequence_id.next_by_id()
        return res

    _name = 'eliterp.request'

    _description = "Requerimiento"

    name = fields.Char(u'Número de Requerimiento')
    type_request = fields.Many2one('eliterp.request.type', u'Tipo de Requerimiento')
    user_id = fields.Many2one('res.users', 'Usuario ')
    comment = fields.Text('Notas')
    user_receiving = fields.Many2one('res.users', u'Usuario Gestión')
    manager_receiving = fields.Many2one('res.users', u'Usuario Aprobación')
    state = fields.Selection([('draft', 'Borrador'),
                              ('sent', 'Enviada'),
                              ('approved', 'Aprobado'),
                              ('denied', 'Negado'),
                              ('solicitud_compra', 'Solicitud de Compra'),
                              ('done', 'Realizado'), ], "Estado", default='draft')
    state_approved = fields.Selection([('pending', 'Pendiente'),
                                       ('approved', 'Aprobada'),
                                       ('denied', 'Negado'),
                                       ('in_process', 'En Proceso'),
                                       ('done', 'Realizado'), ], "Estado")
    state_manager = fields.Selection([('pending', 'Para Aprobación'),
                                      ('denied', 'Negado'),
                                      ('approved_pending', 'Aprobado para Gestión'),
                                      ('done', 'Realizado'), ], "Estado")
    product_lines = fields.One2many('eliterp.request.type.product', 'resquest_id', 'Suministros/Productos')
    type_workflow = fields.Selection([('approved', 'Aprobar'), ('manager', 'Gestionar')], 'Flujo de Requerimiento',
                                     default='manager')
    type_user = fields.Selection([('request', 'Requiere'), ('approved', 'Aprobar'), ('manager', 'Gestor')],
                                 compute='get_type_user', string="Tipo de Usuario")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Centro de Costos')
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    done_date = fields.Datetime('Realizado el')
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)


# MARZ
class EliterpPaymentRequestCancelReason(models.Model):
    _name = 'eliterp.payment.request.cancel.reason'

    _description = 'Modelo - Razón para Negar Solicitud de Pago'

    payment_request_id = fields.Many2one('eliterp.payment.request', required=True)
    description = fields.Text(u'Descripción', required=True)

    def payment_request_cancel(self):
        payment_request_id = self.env['eliterp.payment.request'].browse(self._context['active_id'])
        payment_request_id.write({
            'state': 'denied'
        })
        return payment_request_id


class EliterpPaymentRequestLines(models.Model):
    _name = 'eliterp.payment.request.lines'

    _description = u'Modelo - Líneas de Solicitud de Pago'

    payment_request_id = fields.Many2one('eliterp.payment.request', string="Solicitud")
    detalle = fields.Char(required=True)
    valor_detalle = fields.Float(required=True)


class EliterpPaymentRequest(models.Model):
    @api.multi
    def name_get(self):
        '''Cambiamos columna name del modelo'''
        res = []
        for data in self:
            res.append((data.id, "%s - %s" % (data.beneficiary, data.name)))
        return res

    _name = 'eliterp.payment.request'

    _description = 'Modelo - Solicitud de Pago'

    @api.model
    def _default_journal(self):
        '''Diario'''
        return self.env['account.journal'].search([('name', '=', 'Secuencia de Solicitud de Pago')])[0].id

    @api.model
    def create(self, values):
        payment_request = super(EliterpPaymentRequest, self).create(values)
        payment_request.name = payment_request.journal_id.sequence_id.next_by_id()
        return payment_request

    @api.one
    def _get_total_lines(self):
        '''Actualizamos el Total de Líneas'''
        self.total = sum(line.valor_detalle for line in self.line_payment_request)

    @api.multi
    def approval_solicitud(self):
        self.write({
            'state': 'approved'
        })

    def for_approval_solicitud(self):
        self.write({
            'state': 'for_approved'
        })

    def action_solicitud_cancel_reason(self):
        context = {
            'default_payment_request_id': self.id
        }
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.payment.request.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def print_solicitud_pago(self):
        return self.env['report'].get_action(self, 'elitum_compras.report_solicitud_pago')

    name = fields.Char()
    application_date = fields.Date('Fecha de Solicitud', default=fields.Date.context_today, required=True)
    payment_date = fields.Date('Fecha de Pago', default=fields.Date.context_today, required=True)
    beneficiary = fields.Char('Titular', required=True)
    state = fields.Selection([('entered', 'Borrador'),
                              ('for_approved', 'Para Aprobación'),
                              ('approved', 'Aprobada'),
                              ('paid', 'Pagada'),
                              ('denied', 'Negada'), ], "Estado", default='entered')
    comments = fields.Text('Notas y comentarios')
    documento = fields.Binary(attachment=True)
    documento_name = fields.Char()
    line_payment_request = fields.One2many('eliterp.payment.request.lines', 'payment_request_id',
                                           string='Detalle de Solicitud', required=True)
    total = fields.Float(compute='_get_total_lines', string="Total")
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)


# MARZ
class EliterpTableProvision(models.Model):
    _name = 'eliterp.table.provision'

    _description = u'Modelo - Tabla de Viáticos'

    name = fields.Char('Concepto')
    account_id = fields.Many2one('account.account', string="Cuenta", domain=[('tipo_contable', '=', 'movimiento')])
    max_amount = fields.Float(u'Valor Máximo (Diario)')


class EliterpTableProvisionDestinos(models.Model):
    _name = 'eliterp.table.provision.destinos'

    _description = u'Modelo - Tabla de Viáticos Destinos'

    name = fields.Char('Destino')
    km = fields.Float('Distancia (Km)')
    max_amount = fields.Float(u'Valor (Km)')


class EliterpProvisionCancelReason(models.TransientModel):
    _name = 'eliterp.provision.cancel.reason'

    _description = u'Modelo - Razón para Negar Solicitud de Viático'

    description = fields.Text(u'Descripción', required=True)

    def provision_cancel(self):
        provision_id = self.env['eliterp.provision'].browse(self._context['active_id'])
        provision_id.write({
            'state': 'denied',
            'cancel_reason': self.description
        })
        return provision_id


class EliterpProvisionLines(models.Model):
    _name = 'eliterp.provision.lines'

    _description = u'Modelo - Líneas de Solicitud de Viáticos'

    @api.one
    @api.depends('daily_value', 'days', 'number_of_people')
    def _get_total_line(self):
        self.total = round(float(self.daily_value * self.days * self.number_of_people), 2)

    @api.onchange('table_provision_id')
    def _onchange_table_provision_id(self):
        '''Cambios Valor Diario de Combustible'''
        if self.table_provision_id.name == 'COMBUSTIBLE':
            destino = self.env['eliterp.table.provision.destinos'].search(
                [('id', '=', self.provision_id.destination.id)])
            if self.provision_id.round_trip:
                self.daily_value = destino.max_amount * 2
            else:
                self.daily_value = destino.max_amount
        else:
            self.daily_value = self.table_provision_id.max_amount

    provision_id = fields.Many2one('eliterp.provision', string="Solicitud")
    table_provision_id = fields.Many2one('eliterp.table.provision', string="Concepto")
    daily_value = fields.Float('Valor Diario')
    days = fields.Integer(u'No. Días', default=1)
    number_of_people = fields.Integer('No. Personas', default=1)
    total = fields.Float('Total', compute='_get_total_line')


class EliterpProvision(models.Model):
    @api.multi
    def name_get(self):
        res = []
        for data in self:
            if not data.name:
                res.append((data.id, data.beneficiary.name))
            else:
                res.append((data.id, "%s - %s" % (data.beneficiary.name, data.name)))
        return res

    _name = 'eliterp.provision'

    _description = u'Modelo - Solicitud de Viático'

    def print_solicitud_provision(self):
        return self.env['report'].get_action(self, 'elitum_compras.reporte_solicitud_provision')

    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search([('name', '=', u'Solicitud de Viático')])[0].id

    @api.one
    @api.depends('lines_provision')
    def _get_total_lines(self):
        if self.con_sin_solicitud == 'con_solicitud':
            self.total_solicitud = sum(line.total for line in self.lines_provision)

    @api.model
    def create(self, values):
        if values['con_sin_solicitud'] == 'con_solicitud':
            provision = super(EliterpProvision, self).create(values)
            provision.name = provision.journal_id.sequence_id.next_by_id()
        else:
            provision = super(EliterpProvision, self).create(values)
        return provision

    def action_solicitud_cancel_reason(self):
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.provision.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {},
        }

    @api.multi
    def approval_solicitud(self):
        self.write({
            'state': 'approved',
            'approval_user': self.env.uid
        })

    def for_approval_solicitud(self):
        if not self.lines_provision:
            raise UserError(_("No tiene Líneas de Viáticos"))
        self.write({
            'state': 'for_approved'
        })

    name = fields.Char()
    application_date = fields.Date('Fecha de Solicitud', default=fields.Date.context_today, required=True)
    trip_date = fields.Date('Fecha de Viaje', default=fields.Date.context_today, required=True)
    beneficiary = fields.Many2one('hr.employee', string='Beneficiario', required=True)
    destination = fields.Many2one('eliterp.table.provision.destinos', string='Destino', required=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string="Centro de Costo")
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    reason = fields.Char('Motivo', required=True)
    total_solicitud = fields.Float(compute='_get_total_lines', string="Valor", store=True)
    state = fields.Selection([('entered', 'Borrador'),
                              ('for_approved', 'Para Aprobación'),
                              ('approved', 'Aprobada'),
                              ('managed', 'Gestionada'),
                              ('liquidada', 'Liquidada'),
                              ('denied', 'Negada')], "Estado", default='entered')
    approval_user = fields.Many2one('res.users')
    round_trip = fields.Boolean('Ida y Vuelta', default=False)
    cancel_reason = fields.Text(u'Razón de Negación')
    con_sin_solicitud = fields.Selection([
        ('con_solicitud', 'Con Solicitud'),
        ('sin_solicitud', 'Sin Solicitud'),
    ], default='con_solicitud')
    days_sin_anticipo = fields.Integer(u'No. Días')  # Sin solicitud
    number_of_people = fields.Integer('No. Personas')  # Sin solicitud
    lines_provision = fields.One2many('eliterp.provision.lines', 'provision_id',
                                      string='Líneas de Viáticos')
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)
    move_id = fields.Many2one('account.move', string='Asiento Contable')


class EliterpProvisionLiquidateCancelReason(models.TransientModel):
    _name = 'eliterp.provision.liquidate.cancel.reason'

    _description = u'Modelo - Razón para Negar Liqudación de Viático'

    description = fields.Text(u'Descripción', required=True)

    def provision_cancel(self):
        provision_liquidate_id = self.env['eliterp.provision.liquidate'].browse(self._context['active_id'])
        vouchers_check = provision_liquidate_id.lines_documents_check
        vouchers_check.unlink()  # Borramos los documentos asignados
        provision_liquidate_id.write({
            'state': 'denied',
            'cancel_reason': self.description
        })
        return provision_liquidate_id


class EliterpProvisionVoucher(models.Model):
    _name = 'eliterp.provision.voucher'

    _description = u'Modelo - Comprobante de Viáticos'

    @api.one
    def confirm_voucher(self):
        '''Confirmamos Comprobante'''
        if self.type_voucher == 'invoice':
            if self.have_factura:
                factura = self.env['account.invoice'].search([('voucher_provision_id', '=', self.id)])[0]
                if factura.state == 'draft':
                    raise ValidationError(_("Debe validar la Factura"))
            else:
                raise ValidationError(_("No ha creado factura"))
        else:
            if self.valor == 0.00:
                raise ValidationError(_("Debe especificar valor"))
        return self.write({'state': 'confirm',
                           'name': self.journal_id.sequence_id.next_by_id()})

    def invoice_provision(self):
        '''Creamos la Factura de Provisión'''
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree2')
        form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        context = json.loads(str(action.context).replace("'", '"'))
        context.update({'default_pago_provision': True})
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': context,
            'res_model': action.res_model,
        }
        return result

    def revisar_factura(self):
        '''Mostramos la Factura de Provisión'''
        factura = self.env['account.invoice'].search([('voucher_provision_id', '=', self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree2')
        form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
            'res_id': factura[0].id
        }
        return result

    @api.model
    def _default_journal(self):
        '''Diario'''
        return self.env['account.journal'].search([('name', '=', 'Documento de Viático')])[0].id

    @api.one
    def _get_total(self):
        if self.type_voucher == 'vale':
            self.valor = self.valor_vale
        else:
            factura = self.env['account.invoice'].search([('voucher_provision_id', '=', self.id)])
            if len(factura) != 0:
                self.valor = factura[0].residual

    @api.one
    def _get_number_document(self):
        if self.type_voucher == 'vale':
            self.number_document = self.number_ticket
        else:
            factura = self.env['account.invoice'].search([('voucher_provision_id', '=', self.id)])
            if len(factura) != 0:
                self.number_document = factura[0].numero_factura_interno

    name = fields.Char(string="No. Documento")
    date = fields.Date('Fecha Registro', default=fields.Date.context_today, required=True)
    type_voucher = fields.Selection([
        ('invoice', 'Factura'),
        ('vale', 'Vale')
    ], string="Tipo de Documento", default='invoice')
    table_provision_id = fields.Many2one('eliterp.table.provision', string="Concepto", required=True)
    valor_vale = fields.Float(string="Valor")
    valor = fields.Float(string="Valor", compute='_get_total')
    number_ticket = fields.Char("No. Vale")
    number_document = fields.Char('No. Documento', compute='_get_number_document')
    have_factura = fields.Boolean(default=False)
    state = fields.Selection(
        [('draft', 'Borrador'), ('confirm', 'Confirmado'), ('cancel', 'No Válido')],
        default='draft')
    validate = fields.Boolean(default=False)
    journal_id = fields.Many2one('account.journal', default=_default_journal)


class EliterpProvisionVoucherCheck(models.Model):
    _name = 'eliterp.provision.voucher.check'

    _description = u'Modelo - Comprobante de Viáticos (Check)'

    @api.onchange('approval')
    def _onchange_approval(self):
        '''Actualizamos el Monto dependiendo de la Aprobación'''
        if self.approval == 'total':
            self.monto = self.valor_check

    provision_voucher_id = fields.Many2one('eliterp.provision.voucher', string="No. Documento")
    provision_liquidate_id = fields.Many2one('eliterp.provision.liquidate', string="No. Liquidación")
    date_check = fields.Date('Fecha Registro')
    type_voucher_check = fields.Selection([
        ('invoice', 'Factura'),
        ('vale', 'Vale')
    ], string="Tipo de Documento")
    table_provision_id_check = fields.Many2one('eliterp.table.provision', string="Concepto")
    valor_check = fields.Float(string="Total")
    number_document_check = fields.Char('No. Documento')
    validation_check = fields.Selection([
        ('none', '-'),
        ('no_aprobado', 'Valor no Aprobado'),
        ('no_validate', 'Documento no Válido'),
        ('cargo_empresa', 'Cargo a Empresa')
    ], string="Validación", default='none')
    approval = fields.Selection([
        ('none', '-'),
        ('total', 'Total'),
        ('parcial', 'Parcial')
    ], string="Aprobación", default='none')
    monto = fields.Float(string="Monto")


class EliterpProvisionLiquidate(models.Model):
    _name = 'eliterp.provision.liquidate'

    _description = u'Modelo - Solicitud de Viático Liquidada'

    def print_provision_liquidate(self):
        '''Imprimir Liquidación'''
        return self.env['report'].get_action(self, 'elitum_compras.reporte_provision_liquidate')

    @api.model
    def _default_journal(self):
        '''Diario LIQ'''
        return self.env['account.journal'].search([('name', '=', u'Liquidación de Viático')])[0].id

    def validate_liquidate(self):
        '''Validamos'''
        for line in self.lines_documents_check:
            if line.validation_check == 'none':
                raise UserError(_("Tiene documentos sin realizar la validación"))
        self.write({
            'state': 'validate'
        })

    @api.model
    def create(self, values):
        '''Sobreescribimos método (CREATE) del modelo'''
        # Solicitud sin ancticipo
        if values['have_anticipo'] == 'no':
            attachment = {
                'application_date': values['application_date_tmp'],
                'trip_date': values['trip_date_tmp'],
                'beneficiary': values['beneficiary_tmp'],
                'destination': values['destination_tmp'],
                'account_analytic_id': values['account_analytic_id_tmp'],
                'project_id': values['project_id_tmp'],
                'reason': values['reason_tmp'],
                'days_sin_anticipo': values['days_sin_anticipo_tmp'],
                'number_of_people': values['number_of_people_tmp'],
                'round_trip': values['round_trip_tmp'],
                'con_sin_solicitud': 'sin_solicitud',
                'state': 'for_approved'
            }
            object = self.env['eliterp.provision'].create(attachment)
            values.update({
                'show_have_anticipo': True,
                'provision_id': object.id
            })
        # Solicitud con anticipo
        else:
            values.update({
                'show_have_anticipo': True
            })
        provision_liquidate = super(EliterpProvisionLiquidate, self).create(values)
        provision_liquidate.name = provision_liquidate.journal_id.sequence_id.next_by_id()
        return provision_liquidate

    def action_liquidate_cancel_reason(self):
        '''Díalogo para Anulación'''
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.provision.liquidate.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {},
        }

    @api.multi
    def approval_liquidate(self):
        '''Aprobar Liquidación'''
        self.write({
            'state': 'approved',
            'approval_user': self.env.uid
        })

    def for_approval_liquidate(self):
        '''Solicitar Aprobación'''
        if not self.lines_documents_check:
            raise UserError(_("No tiene Líneas de Documentos"))
        self.write({
            'state': 'for_approved'
        })

    def cargar_documentos(self):
        '''Cargar Documentos'''
        voucher_list = self.env['eliterp.provision.voucher'].search([
            ('create_uid', '=', self.env.uid),
            ('state', '=', 'confirm'),
            ('validate', '=', False)
        ])
        list_lines = []
        for voucher in voucher_list:
            list_lines.append([0, 0, {'provision_voucher_id': voucher.id,
                                      'date_check': voucher.date,
                                      'type_voucher_check': voucher.type_voucher,
                                      'table_provision_id_check': voucher.table_provision_id,
                                      'valor_check': voucher.valor,
                                      'number_document_check': voucher.number_document}])
        return self.update({
            'lines_documents_check': list_lines
        })

    @api.depends('lines_documents_check')
    def _get_diferencia(self):
        if self.have_anticipo == 'yes':
            suma_montos = sum(line['monto'] for line in self.lines_documents_check)
            diferencia = self.provision_id.total_solicitud - suma_montos
            self.diferencia = round(diferencia, 2)
        else:
            self.diferencia = sum(line['monto'] for line in self.lines_documents_check)

    def liquidate(self):
        '''Liquidamos'''
        cuenta_provisiones = self.env['account.account'].search([('code', '=', '1.1.2.3.9')])
        # Validamos exista cuenta de Provisiones
        if not cuenta_provisiones:
            raise UserError(_("No existe Cuenta de Viáticos creada"))
        # Validamos qué el Benficiario tenga Cuenta
        if not self.provision_id.beneficiary.account_advance_payment:
            raise UserError(_("No tiene Cuenta asignada al Empleado/a"))
        cuenta_empleado = self.provision_id.beneficiary.account_advance_payment
        list_movimientos = []
        for line in self.lines_documents_check:
            # Documento no Válido
            if line.validation_check == 'no_validate':
                line.provision_voucher_id.write({'state': 'cancel'})
            # Cargo A Empresa, Valor no Aprobado
            else:
                cuenta = ''
                partner = ''
                if line.type_voucher_check == 'invoice':
                    factura = self.env['account.invoice'].search(
                        [('voucher_provision_id', '=', line.provision_voucher_id.id)])
                    partner = factura.partner_id.id
                    cuenta = factura.account_id.id
                else:
                    partner = ''
                    cuenta = line.table_provision_id_check.account_id.id
                list_movimientos.append({
                    # True -> Debe, False -> Haber
                    'type': True,
                    'partner': partner,
                    'nombre': line.table_provision_id_check.name,
                    'cuenta': cuenta,
                    'valor': line.monto
                })
                list_movimientos.append({
                    'type': False,
                    'partner': partner,
                    'nombre': line.table_provision_id_check.name,
                    'cuenta': cuenta_provisiones.id,
                    'valor': line.monto
                })
            # Documentos ya procesados
            line.provision_voucher_id.write({'validate': True})
        # Generamos Asiento Contable
        fecha_actual = fields.Date.today()
        move_id = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'date': fecha_actual
        })
        for register in list_movimientos:
            # Línea del Debe
            if register['type']:
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': register['nombre'],
                    'journal_id': self.journal_id.id,
                    'partner_id': register['partner'],
                    'account_id': register['cuenta'],
                    'move_id': move_id.id,
                    'debit': register['valor'],
                    'credit': 0.0,
                    'date': fecha_actual
                })
            # Línea del Haber
            else:
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': register['nombre'],
                    'journal_id': self.journal_id.id,
                    'partner_id': register['partner'],
                    'account_id': register['cuenta'],
                    'move_id': move_id.id,
                    'debit': 0.0,
                    'credit': register['valor'],
                    'date': fecha_actual
                })
        # Línea de Diferencia
        if self.diferencia > 0 or self.have_anticipo == 'no':
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': cuenta_empleado.name,
                'journal_id': self.journal_id.id,
                'partner_id': '',
                'account_id': cuenta_empleado.id,
                'move_id': move_id.id,
                'debit': self.diferencia,
                'credit': 0.0,
                'date': fecha_actual
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': cuenta_provisiones.name,
                'journal_id': self.journal_id.id,
                'partner_id': '',
                'account_id': cuenta_provisiones.id,
                'move_id': move_id.id,
                'debit': 0.0,
                'credit': self.diferencia,
                'date': fecha_actual
            })

        if self.diferencia < 0 and self.have_anticipo == 'yes':
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': cuenta_provisiones.name,
                'journal_id': self.journal_id.id,
                'partner_id': '',
                'account_id': cuenta_provisiones.id,
                'move_id': move_id.id,
                'debit': self.diferencia,
                'credit': 0.0,
                'date': fecha_actual
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': cuenta_empleado.name,
                'journal_id': self.journal_id.id,
                'partner_id': '',
                'account_id': cuenta_empleado.id,
                'move_id': move_id.id,
                'debit': self.diferencia,
                'credit': 0.0,
                'date': fecha_actual
            })
        move_id.with_context(asientos_eliterp=True, name_asiento=self.name).post()
        move_id.write({'ref': self.name})
        # Liquidamos la Solicitud/Sin Solicitud
        self.provision_id.write({'state': 'liquidada'})
        self.write({
            'state': 'liquidada',
            'move_id': move_id.id
        })

    name = fields.Char()
    show_have_anticipo = fields.Boolean(default=False)
    have_anticipo = fields.Selection([
        ('yes', 'Sí'),
        ('no', 'No')
    ], u'Recibió Anticipo', default='yes')
    provision_id = fields.Many2one('eliterp.provision', 'No. Documento')
    # Campos relacionados con la Solicitud
    application_date = fields.Date(related='provision_id.application_date')
    trip_date = fields.Date(related='provision_id.trip_date')
    beneficiary = fields.Many2one(related='provision_id.beneficiary')
    destination = fields.Many2one(related='provision_id.destination')
    account_analytic_id = fields.Many2one(related='provision_id.account_analytic_id')
    project_id = fields.Many2one(related='provision_id.project_id')
    days_sin_anticipo = fields.Integer(related='provision_id.days_sin_anticipo')
    number_of_people = fields.Integer(related='provision_id.number_of_people')
    reason = fields.Char(related='provision_id.reason')
    total_solicitud = fields.Float(related='provision_id.total_solicitud')
    round_trip = fields.Boolean(related='provision_id.round_trip')
    # Campos sin Solicitud (Formulario)
    application_date_tmp = fields.Date('Fecha de Solicitud', default=fields.Date.context_today, store=False)
    trip_date_tmp = fields.Date('Fecha de Viaje', default=fields.Date.context_today, store=False)
    beneficiary_tmp = fields.Many2one('hr.employee', string='Beneficiario', store=False)
    destination_tmp = fields.Many2one('eliterp.table.provision.destinos', string="Destino", store=False)
    account_analytic_id_tmp = fields.Many2one('account.analytic.account', string="Centro de Costo", store=False)
    project_id_tmp = fields.Many2one('eliterp.project', 'Proyecto', store=False)
    reason_tmp = fields.Char('Motivo', store=False)
    days_sin_anticipo_tmp = fields.Integer(u'No. Días', store=False)
    number_of_people_tmp = fields.Integer('No. Personas', store=False)
    round_trip_tmp = fields.Boolean('Ida y Vuelta', default=False, store=False)
    approval_user = fields.Many2one('res.users')
    cancel_reason = fields.Text(u'Razón de Negación')
    move_id = fields.Many2one('account.move', string='Asiento Contable')
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)
    notas = fields.Text()
    state = fields.Selection([('entered', 'Borrador'),
                              ('for_approved', 'Para Aprobación'),
                              ('approved', 'Aprobada'),
                              ('validate', 'Validada'),
                              ('liquidada', 'Liquidada'),
                              ('denied', 'Negada')], "Estado", default='entered')
    lines_documents_check = fields.One2many('eliterp.provision.voucher.check', 'provision_liquidate_id',
                                            string="Líneas de Documentos")
    diferencia = fields.Float(compute='_get_diferencia', store=True)
