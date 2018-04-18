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

from odoo.exceptions import UserError
from odoo import api, fields, models, _
import datetime


class LinesAccountPeriod(models.Model):
    _name = 'lines.account.period'

    _description = u'Líneas de Período Contable'

    name = fields.Char('Nombre')
    mes = fields.Char('Mes')
    code = fields.Integer(u'Código')
    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_cierre = fields.Date('Fecha Cierre')
    periodo_id = fields.Many2one('account.period', u'Período')


class AccountPeriod(models.Model):
    _name = 'account.period'

    _description = u'Período Contable'

    def _get_mes(self, mes):
        if mes == 1:
            return "Enero"
        if mes == 2:
            return "Febrero"
        if mes == 3:
            return "Marzo"
        if mes == 4:
            return "Abril"
        if mes == 5:
            return "Mayo"
        if mes == 6:
            return "Junio"
        if mes == 7:
            return "Julio"
        if mes == 8:
            return "Agosto"
        if mes == 9:
            return "Septiembre"
        if mes == 10:
            return "Octubre"
        if mes == 11:
            return "Noviembre"
        if mes == 12:
            return "Diciembre"

    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def cargar_meses(self):
        if self.ano_contable < 1990 and self.ano_contable > 3000:
            raise UserError("Ingreso un Año Contable válido")
        if len(self.lineas_periodo) >= 12:
            raise UserError("No puede asignar más meses al Año Contable")
        list_lines = []
        for x in range(1, 13):
            list_lines.append([0, 0, {'code': x,
                                      'name': self._get_mes(x) + " del " + str(self.ano_contable),
                                      'mes': self._get_mes(x),
                                      'fecha_inicio': datetime.date(self.ano_contable, x, 1),
                                      'fecha_cierre': self.last_day_of_month(datetime.date(self.ano_contable, x, 1))}])
        return self.update({'lineas_periodo': list_lines, 'name': self.ano_contable})

    name = fields.Char(u'Período')
    ano_contable = fields.Integer(u'Año Contable', size=4)
    fecha_inicio = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    lineas_periodo = fields.One2many('lines.account.period', 'periodo_id', u'Líneas de Período')


class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"

    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='all')


class ResBank(models.Model):
    _inherit = 'res.bank'

    type_action = fields.Selection([('charges', 'Cobros'), ('payments', 'Pagos')], string='Tipo de Uso',
                                   default='charges')
    account_id = fields.Many2one('account.account', string='Cuenta', domain=[('tipo_contable', '=', 'movimiento')])
    numero_cuenta = fields.Char('No. Cuenta')
    inicio_secuencia = fields.Integer('Inicio Secuencia')
    fin_secuencia = fields.Integer('Fin Secuencia')
    padding = fields.Integer(u'Dígitos', default=7)
    numero_siguiente = fields.Integer('No. Siguiente')


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def create(self, vals):
        company_id = vals.get('company_id', self.env.user.company_id.id)
        if vals.get('type') in ('bank', 'cash'):
            # For convenience, the name can be inferred from account number
            if not vals.get('name') and 'bank_acc_number' in vals:
                vals['name'] = vals['bank_acc_number']
            # If no code provided, loop to find next available journal code
            if not vals.get('code'):
                journal_code_base = (vals['type'] == 'cash' and 'CSH' or 'BNK')
                journals = self.env['account.journal'].search(
                    [('code', 'like', journal_code_base + '%'), ('company_id', '=', company_id)])
                for num in xrange(1, 100):
                    # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
                    journal_code = journal_code_base + str(num)
                    if journal_code not in journals.mapped('code'):
                        vals['code'] = journal_code
                        break
                else:
                    raise UserError(_("Cannot generate an unused journal code. Please fill the 'Shortcode' field."))

            # Create a default debit/credit account if not given
            default_account = vals.get('default_debit_account_id') or vals.get('default_credit_account_id')
            if not default_account:
                company = self.env['res.company'].browse(company_id)
                account_vals = self._prepare_liquidity_account(vals.get('name'), company, vals.get('currency_id'),
                                                               vals.get('type'))
                default_account = self.env['account.account'].create(account_vals)
                vals['default_debit_account_id'] = default_account.id
                vals['default_credit_account_id'] = default_account.id

        ''''''
        '''Se quita la secuencia para poder seleccionarla desde el formulario
        '''

        # We just need to create the relevant sequences according to the chosen options
        # if not vals.get('sequence_id'):
        #     vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
        # if vals.get('type') in ('sale', 'purchase') and vals.get('refund_sequence') and not vals.get('refund_sequence_id'):
        #     vals.update({'refund_sequence_id': self.sudo()._create_sequence(vals, refund=True).id})

        journal = super(AccountJournal, self).create(vals)

        # Create the bank_account_id if necessary
        if journal.type == 'bank' and not journal.bank_account_id and vals.get('bank_acc_number'):
            journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))

        return journal

    code = fields.Char(string='Short Code')


class account_account_type(models.Model):
    _inherit = "account.account.type"

    type = fields.Selection([('other', 'Regular'),
                             ('receivable', 'Receivable'),
                             ('payable', 'Payable'),
                             ('liquidity', 'Liquidity'),
                             ('bank', 'Banco'), ], default='other',
                            help="The 'Internal Type' is used for features available on " \
                                 "different types of accounts: liquidity type is for cash or bank accounts" \
                                 ", payable/receivable is for vendor/customer accounts.")


class account_account(models.Model):
    _inherit = "account.account"

    tipo_contable = fields.Selection([('vista', 'Vista'),
                                      ('movimiento', 'Movimiento'), ], 'Tipo de Cuenta', required=True,
                                     default='movimiento', )

    # MARZ
    saldo_inicial = fields.Float('Saldo Inicial', help="Este valor sirve para inicio de una Compañía")
    fecha_saldo_inicial = fields.Date('Fecha Saldo Inicial')


class PlannerAccount(models.Model):
    _inherit = 'web.planner'

    def _prepare_planner_account_data(self):
        values = {
            'company_id': self.env.user.company_id,
            'is_coa_installed': bool(self.env['account.account'].search_count([])),
            'payment_term': self.env['account.payment.term'].search([])
        }
        return values


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    transfer_account_id = fields.Many2one('account.account',
                                          domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=',
                                                                                          self.env.ref(
                                                                                              'account.data_account_type_current_assets').id),
                                                               ('tipo_contable', '=', 'movimiento')],
                                          help="Intermediary account used when moving money from a liquidity account to another",
                                          required=False)


# MARZ
class EliterpSaldosInicialesBeneficiosLines(models.Model):
    _name = 'eliterp.saldos.beneficios.sociales.lines'

    _description = u'Modelo - Líneas Saldos Beneficios Sociales'

    beneficio_social_id = fields.Many2one('eliterp.saldos.beneficios.sociales')
    rubro = fields.Selection([
        ('decimo_tercero', 'Décimo Tercer Sueldo'),
        ('decimo_cuarto', 'Décimo Cuarto Sueldo'),
        ('fondos_reserva', 'Fondos de Reserva'),
        ('vacaciones', 'Vacaciones')
    ], default='decimo_tercero', required=True, string='Rubro')
    valor = fields.Float(required=True, string='Valor')
    fecha = fields.Integer(required=True, string=u"Año Contable", size=4)
    novedades = fields.Text(string='Novedades')


class EliterpSaldosInicialesBeneficios(models.Model):
    _name = 'eliterp.saldos.beneficios.sociales'

    _description = u'Modelo - Saldos Beneficios Sociales'

    name = fields.Many2one('hr.employee', required=True, string='Empleado', domain=[('state_laboral', '=', 'activo')])
    wage = fields.Float(required=True, string='Sueldo')
    status = fields.Boolean(default=True, string='Activo?')
    lines_rubro = fields.One2many('eliterp.saldos.beneficios.sociales.lines', 'beneficio_social_id')
