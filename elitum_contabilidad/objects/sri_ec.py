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


# MARZ
class TablaImpuestoRenta(models.Model):
    _name = 'eliterp.tabla.impuesto.renta'

    _description = 'Tabla del Impuesto a la Renta'

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "Registro %s" % (data.id)))
        return res

    fraccion_basica = fields.Float(required=True)
    exceso_hasta = fields.Float(required=True)
    impuesto_fraccion_basica = fields.Float(required=True)
    impuesto_fraccion_excedente = fields.Float(required=True)
    status = fields.Boolean(default=True)


class EliterpTipoDocumento(models.Model):
    _name = 'eliterp.type.document'

    _description = 'Tipos de Documento ATS'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string=u'Código', size=2, required=True)
    sustento_ids = fields.Many2many('sustento.tributario',
                                    'rel_type_document_sustento_ids',
                                    'type_document_id',
                                    'sustento_tributario_id',
                                    'Sustentos Tributarios')
    status = fields.Boolean(default=True)


class SustentoTributario(models.Model):
    _name = 'sustento.tributario'

    _description = 'Sustento Tributario'

    name = fields.Char('Nombre', required=True)
    codigo = fields.Char(u'Código', required=True)


class AutorizacionSri(models.Model):
    _name = 'autorizacion.sri'

    _description = u'Autorización SRI'

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "%s - %s" % (data.tipo_comprobante.name, data.numero_autorizacion)))
        return res

    @api.model
    def create(self, values):
        if values['tipo_comprobante'] == 1:
            numero = values['numero_autorizacion']
            new_sequence_withhold = self.env['ir.sequence'].create({'name': u"Retención" + "-" + numero,
                                                                    'code': values['numero_autorizacion'],
                                                                    'prefix': values['numero_establecimiento'] + "-" +
                                                                              values['punto_emision'] + "-",
                                                                    'padding': 10
                                                                    })
            values.update({'sequence_id': new_sequence_withhold.id})
        return super(AutorizacionSri, self).create(values)

    numero_establecimiento = fields.Char('No. Establecimiento')
    punto_emision = fields.Char('Punto Emisión')
    secuencial_inico = fields.Integer(u'Secuencial Inicio')
    secuencial_fin = fields.Integer(u'Secuencial Fin')
    secuencia = fields.Integer('Próximo No.', default=1)
    numero_autorizacion = fields.Char('No. Autorización', required=True)
    tipo_comprobante = fields.Many2one('eliterp.type.document', 'Tipo Documento', required=True)
    state = fields.Selection([('activo', 'Activo'),
                              ('terminado', 'Terminado')], string="Estado", default='activo')
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia')


class AccountJournalPaymentMethod(models.Model):
    _name = 'account.journal.payment.method'

    _description = u'Forma de Pago'

    @api.multi
    def name_get(self):
        res = []
        name_code = []
        for name in self:
            name_code = []
            name_code.append(name.id)
            name_code.append(name.code + " - " + name.name)
            res.append(name_code)
        return res

    code = fields.Char('Código')
    prioridad = fields.Integer('Prioridad')
    name = fields.Char('Nombre')


class CreditoTributario(models.Model):
    _name = 'credito.tributario'

    _description = u'Crédito Tributario'

    @api.multi
    def name_get(self):
        res = []
        name_code = []
        for name in self:
            name_code = []
            name_code.append(name.id)
            name_code.append(u"Crédito de " + name.ano_contable.name + " - " + name.period_id.name)
            res.append(name_code)
        return res

    name = fields.Char('Nombre')
    ano_contable = fields.Many2one(
        'account.period',
        u'Año Contable',
        required=True
    )
    period_id = fields.Many2one(
        'lines.account.period',
        'Período',
        required=True
    )
    mes = fields.Integer(related="period_id.code", store=True)
    ano = fields.Integer(related="ano_contable.ano_contable", store=True)
    valor = fields.Float("Valor IVA", required=True)
    valor_renta = fields.Float(u"Valor Retención IVA", required=True)
    novedades = fields.Text(string='Novedades')
