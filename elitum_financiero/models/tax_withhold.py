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
from odoo.exceptions import except_orm, ValidationError
from datetime import datetime, timedelta


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def name_get(self):
        '''Cambios nombre a mostrar del modelo'''
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Refund'),
            'in_refund': _('Vendor Refund'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.numero_factura or TYPES[inv.type], inv.name or '')))
        return result

    @api.multi
    def add_withhold_eliterp(self):
        '''Diálogo para Retención'''
        view = self.env.ref('elitum_financiero.eliterp_retenciones_view_form_compras_wizard')
        context = {'default_invoice_id': self.id,
                   'default_partner_id': self.partner_id.id,
                   'default_type': 'purchase',
                   'default_base_iva': self.amount_tax,
                   'default_base_imponible': self.amount_untaxed}
        return {
            'name': "Retención",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'tax.withhold',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    withhold_id = fields.Many2one('tax.withhold', string='Retención')
    factura_vieja = fields.Boolean('Es Factura vieja?', default=False)
    numero_retencion = fields.Char(u'No. Retención', related='withhold_id.name_retencion')


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def name_get(self):
        '''Cambios nombre a mostrar del modelo'''
        res = []
        for name in self:
            tax_name = []
            tax_name.append(name.id)
            if name.tipo_impuesto == 'retencion':
                tax_name.append(str(name.code_name) + " - " + name.name)
            else:
                tax_name.append(name.name)
            res.append(tax_name)
        return res


class LineTaxWithhold(models.Model):
    _name = 'line.tax.withhold'

    _description = 'Linea de Impuesto Retencion'

    @api.onchange('tipo_retencion')
    def _onchange_tipo_retencion(self):
        '''Evento al cambiar Tipo de Retención, calculamos Monto'''
        if self.tipo_retencion == False:
            return
        if self.tipo_retencion == 'iva':
            self.base_imponible = self.withhold_id.base_iva
        if self.tipo_retencion == 'renta':
            self.base_imponible = self.withhold_id.base_imponible

    @api.onchange('retencion')
    def _onchange_retencion(self):
        '''Evento al cambiar Retención, actualizamos Monto'''
        self.monto = (self.retencion.amount * self.base_imponible) / 100

    tipo_retencion = fields.Selection([('iva', 'Iva'), ('renta', 'Renta')], string='Tipo')
    retencion = fields.Many2one('account.tax', string=u'Retención')
    base_imponible = fields.Float(string='Base Imponible')
    monto = fields.Float('Monto')
    withhold_id = fields.Many2one('tax.withhold', string=u'Retención')
    tax_id = fields.Many2one('account.invoice.tax', string=u'Impuesto de Retención')


class WithholdCancelReason(models.Model):
    _name = 'withhold.cancel.reason'

    _description = 'Razon Cancelar Retencion'

    def cancel_reason_withhold_move(self):
        '''Cancelamos la Retención'''
        withhold_id = self.env['tax.withhold'].browse(self._context['active_id'])
        withhold_id.move_id.with_context(from_retencion=True).reverse_moves(withhold_id.fecha,
                                                                            withhold_id.journal_id or False)
        withhold_id.move_id.write({'state': 'cancel', 'ref': self.description})
        withhold_id.cancel_withhold()
        return True

    description = fields.Text(u'Descripción', required=True)

    def confirm_cancel_reason(self):
        invoice = self.env['account.invoice'].browse(self._context['active_id'])
        invoice.action_cancel()
        invoice.move_id.write({'ref': self.description})
        return True


class TaxWithhold(models.Model):
    _name = 'tax.withhold'

    _description = u'Retención'

    def cancel_reason_withhold(self):
        '''Díalogo de Cancelación'''
        context = dict(self._context or {})
        if self.state == 'draft':
            return self.cancel_withhold()
        else:
            return {
                'name': "Explique la Razón",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'withhold.cancel.reason',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context,
            }

    @api.one
    def cancel_withhold(self):
        '''Anular Retención (Compras/Ventas)'''
        self.invoice_id.write({'withhold_id': False,
                               'have_withhold': False})
        invoice_tax = self.env['account.invoice.tax'].search([('invoice_id', '=', self.invoice_id.id),
                                                              ('name', '=', self.line_tax_withhold.retencion.name),
                                                              ('tax_id', '=', self.line_tax_withhold.retencion.id),
                                                              ('account_id', '=',
                                                               self.line_tax_withhold.retencion.account_id.id)])[0]
        invoice_tax.unlink()
        self.invoice_id._compute_amount()
        self.invoice_id._compute_residual()
        self.write({
            'state': 'cancel', 'name_retencion': False
        })
        return True

    @api.one
    def confirm_withhold(self):
        '''Confirmar Retención'''
        journal_id = self.env['account.journal'].search([('name', '=', 'Retención Venta')])
        move_id = self.env['account.move'].create({
            'journal_id': journal_id.id,
            'ref': u'Retención de Factura ' + self.invoice_id.numero_factura,
            'date': self.fecha
        })
        line_move_retencion = self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': self.partner_id.name,
             'journal_id': journal_id.id,
             'partner_id': self.invoice_id.partner_id.id,
             'account_id': self.partner_id.property_account_receivable_id.id,
             'move_id': move_id.id,
             'credit': self.monto_total,
             'debit': 0.0,
             'date': self.fecha
             })
        count = len(self.line_tax_withhold)
        for line in self.line_tax_withhold:
            count -= 1
            if count == 0:
                move_line = self.env['account.move.line']
            else:
                move_line = self.env['account.move.line'].with_context(check_move_validity=False)
            move_line.create({'name': line.retencion.name,
                              'account_id': line.retencion.account_id.id,
                              'partner_id': self.invoice_id.partner_id.id,
                              'journal_id': journal_id.id,
                              'move_id': move_id.id,
                              'credit': 0.0,
                              'debit': line.monto,
                              'date': self.fecha
                              })
        move_id.post()
        self.name = move_id.name
        line_move_factura = self.invoice_id.move_id.line_ids.filtered(
            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
        (line_move_factura + line_move_retencion).reconcile()
        self.invoice_id._compute_amount()
        self.invoice_id._compute_residual()
        return self.write({
            'state': 'confirm',
            'move_id': move_id.id
        })

    @api.one
    def _get_total_lines(self):
        '''Monto Total de Retención'''
        self.monto_total = sum(line.monto for line in self.line_tax_withhold)

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        '''Evento generado al cambiar de Factura'''
        self.base_imponible = self.invoice_id.amount_untaxed
        self.base_iva = self.invoice_id.amount_tax

    @api.multi
    def write(self, values):
        '''Sobreescribimos método (PUT) del modelo tax.withhold'''
        if 'line_tax_withhold' in values:
            for line in values['line_tax_withhold']:
                if line[0] == 0:
                    retencion = self.env['account.tax'].browse(line[2]['retencion'])
                    monto = line[2]['monto'] if 'monto' in line[2] else 0.00
                    self.env['account.invoice.tax'].create({
                        'invoice_id': self.invoice_id.id,
                        'name': retencion.name,
                        'tax_id': retencion.id,
                        'account_id': retencion.account_id.id,
                        'amount': -1 * monto
                    })
                if line[0] == 1:
                    retencion = self.env['account.tax'].browse(line[2]['retencion'])
                    if self.line_tax_withhold.tax_id:
                        self.line_tax_withhold.tax_id.write({
                            'name': retencion.name,
                            'tax_id': retencion.id,
                            'account_id': retencion.account_id.id,
                            'amount': line[2]['monto'] if 'monto' in line[2] else 0.00
                        })
                    else:
                        withhold_line = self.line_tax_withhold.browse(line[1])
                        monto = line[2]['monto'] if 'monto' in line[2] else 0.00
                        invoice_tax = self.env['account.invoice.tax'].search([('invoice_id', '=', self.invoice_id.id),
                                                                              ('name', '=',
                                                                               withhold_line.retencion.name),
                                                                              ('tax_id', '=',
                                                                               withhold_line.retencion.id),
                                                                              ('account_id', '=',
                                                                               withhold_line.retencion.account_id.id)])[
                            0]
                        invoice_tax.write({
                            'name': retencion.name,
                            'tax_id': retencion.id,
                            'account_id': retencion.account_id.id,
                            'amount': -1 * monto
                        })
                if line[0] == 2:
                    if self.factura_modificada == False:
                        if self.line_tax_withhold.tax_id:
                            self.line_tax_withhold.tax_id.unlink()
                        else:
                            withhold_line = self.line_tax_withhold.browse(line[1])
                            invoice_tax = \
                                self.env['account.invoice.tax'].search([('invoice_id', '=', self.invoice_id.id),
                                                                        ('name', '=', withhold_line.retencion.name),
                                                                        ('tax_id', '=', withhold_line.retencion.id),
                                                                        ('account_id', '=',
                                                                         withhold_line.retencion.account_id.id)])[0]
                            invoice_tax.unlink()
                    else:
                        values.update({'factura_modificada': False})
            self.invoice_id._compute_amount()
            self.invoice_id._compute_residual()
        return super(TaxWithhold, self).write(values)

    @api.model
    def create(self, values):
        '''Sobreescribimos método (CREATE) del modelo tax.withhold'''
        self.env['eliterp.funciones'].validar_periodo(values['fecha'])
        obj_sequence = self.env['ir.sequence']
        if values['type'] == 'purchase':
            if values['if_secuencial'] == True:
                autorizacion = self.env['autorizacion.sri'].search([('code_comprobante', '=', '07'), ('state', '=', 'activo')])
                if not autorizacion:
                    raise except_orm("Error", "No hay Autorización activa del SRI para Retención de Compra")
                else:
                    sequence = obj_sequence.next_by_code(autorizacion[0].numero_autorizacion)
                    # Verificamos secuencia si es mayor no validamos y le cambiamos el estado
                    n_s = int(sequence[8:])
                    if n_s == autorizacion.secuencial_fin:
                        autorizacion._update_state()
                    values.update({'name_retencion': sequence})
            if 'if_secuencial' in values:
                if values['if_secuencial'] == False:
                    values.update({
                        'name_retencion': self.env['ir.sequence'].next_by_code('procesos.internos')
                    })
        invoice = self.env['account.invoice'].browse(values['invoice_id'])
        invoice.write({'have_withhold': True})
        retencion = super(TaxWithhold, self).create(values)
        invoice.write({'withhold_id': retencion.id})
        invoice_tax = self.env['account.invoice.tax']
        for line in retencion.line_tax_withhold:
            tax_id = invoice_tax.create({
                'invoice_id': values['invoice_id'],
                'name': line.retencion.name,
                'tax_id': line.retencion.id,
                'account_id': line.retencion.account_id.id,
                'amount': -1 * line.monto
            })
            line.write({'tax_id': tax_id.id})
        invoice._compute_amount()
        return retencion

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(TaxWithhold, self).fields_get(allfields=allfields, attributes=attributes)
        if 'partner_id' in res and 'default_type' in self.env.context:
            if self.env.context['default_type'] == 'sale':
                res['partner_id']['string'] = 'Cliente'
            if self.env.context['default_type'] == 'purchase':
                res['partner_id']['string'] = 'Proveedor'
        return res

    def _get_journal(self):
        '''Diario por defecto de Retención'''
        if self._context['default_type'] == 'sale':
            return self.env['account.journal'].search([('name', '=', 'Retención Venta')])[0].id
        else:
            return self.env['account.journal'].search([('name', '=', 'Retención Compra')])[0].id

    def get_ano_fiscal(self, fecha):
        fecha_convert = datetime.strptime(fecha, "%Y-%m-%d")
        return fecha_convert.year

    def imprimir_retencion_venta(self):
        reporte = []
        reporte.append(self.id)
        lista = []
        for line in self.line_tax_withhold:
            lista.append({
                'anio': self.get_ano_fiscal(self.fecha),
                'imponible': '{:,.2f}'.format(line.base_imponible),
                'tipo': line.tipo_retencion.upper(),
                'code': line.retencion.code_name,
                'porc': line.retencion.amount,
                'valor': '{:,.2f}'.format(line.monto)

            })
        result = {
            'type': 'ir.actions.report.xml',
            'report_name': 'elitum_financiero.reporte_retencion_venta',
            'datas': {'ids': reporte},
            'context': {
                'Retencion': True,
                'proveedor': self.partner_id.name,
                'cedula': self.partner_id.vat_eliterp,
                'calle': self.partner_id.street,
                'fecha': self.fecha,
                'factura': self.invoice_id.numero_factura_interno,
                'total': '{:,.2f}'.format(sum(x.monto for x in self.line_tax_withhold)),
                'get_lines': lista
            }
        }
        return result

    name = fields.Char(u'Número de Comprobante')
    name_retencion = fields.Char(u'Número de Retención', default='001-001-')
    base_imponible = fields.Float('Base Imponible')
    base_iva = fields.Float('Base Iva')
    fecha = fields.Date('Fecha de Emisión', default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='Cliente/Proveedor')
    invoice_id = fields.Many2one('account.invoice', u'Factura')
    type = fields.Selection([('sale', 'Venta'), ('purchase', 'Compra')], string='Tipo')
    state = fields.Selection([('draft', 'Borrador'),
                              ('confirm', 'Aprobada'),
                              ('cancel', 'Anulada')], string=u'Estado', default='draft')
    line_tax_withhold = fields.One2many('line.tax.withhold', 'withhold_id', string=u'Línea de Retenciones')
    monto_total = fields.Float(compute='_get_total_lines', string="Total")
    if_secuencial = fields.Boolean(string='Secuencial?')
    journal_id = fields.Many2one('account.journal', string="Diario", default=_get_journal, store=True, readonly="1")
    move_id = fields.Many2one('account.move', string='Asiento Contable')
    numero_intero_retencion = fields.Integer(u'Número Interno')
    factura_modificada = fields.Boolean(default='False')

    _sql_constraints = [
        ('name_retencion_uniq', 'unique (name_retencion)', "El número de Retención ya esta registrado")]
