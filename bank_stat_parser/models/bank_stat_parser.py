# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

class BankStatParser(models.Model):
    _name = 'bank.stat.parser'
    _description = 'Bank Statement Parser'

    # name = fields.Char(string='Название')

    # Определение модели
    # С заранее определёнными полями, если необходимо
    # Модель может включать функции обработки и фактического парсинга выписок

    class AccountPayment(models.Model):
        _inherit = 'account.payment'

        # Создание платежей из вложений XML
        @api.model
        def create_payments_from_xml_attachment(self, attachment_ids):
            """
            Обрабатывает XML вложения и создает платежи на их основе.
            """
            if not isinstance(attachment_ids, list):
                attachment_ids = [attachment_ids]

            for attachment_id in attachment_ids:
                attachment = self.env['ir.attachment'].browse(attachment_id)
                if attachment:
                    try:
                        content_data = base64.b64decode(attachment.datas)
                        xml_tree = etree.fromstring(content_data)
                        payments_data = self.parse_xml_content(xml_tree)
                        for payment_data in payments_data:
                            self.create(payment_data)
                        _logger.info(f"Successfully created payments from attachment: {attachment.name}")
                    except etree.XMLSyntaxError as e:
                        _logger.error(f"XML Syntax Error in attachment: {attachment.name}, error: {e}")
                    except Exception as e:
                        _logger.error(f"Error processing attachment: {attachment.name}, error: {e}")
                else:
                    _logger.warning(f"Attachment with ID {attachment_id} does not exist.")

        # Парсинг XML и получение данных для платежей
        def parse_xml_content(self, xml_tree):
            """
            Парсит XML и возвращает список данных для создания платежей.
            """
            payments_data = []
            payment_elements = xml_tree.findall(".//turns")
            for payment_element in payment_elements:
                partner_name = payment_element.find('.//corrName').text
                partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({'name': partner_name})

                xml_currency_code = payment_element.find('.//currCode').text \
                    if payment_element.find('.//currCode') is not None \
                    else self.env.company.currency_id.name
                currency = self.env['res.currency'].search([('name', '=', xml_currency_code)], limit=1)
                if not currency:
                    currency = self.env.company.currency_id

                payment_values = {
                    'amount': float(payment_element.find('.//dbAmount').text or 0.0),
                    'payment_date': fields.Date.from_string(payment_element.find('.//docDate').text),
                    'communication': payment_element.find('.//naznText').text,
                    'ref': payment_element.getparent().find('.//account').text,
                    'partner_id': partner.id,
                    'currency_id': currency.id,
                    # Добавьте любые другие необходимые поля и их обработку
                }
                payments_data.append(payment_values)

            return payments_data