from odoo import models, fields, api
from lxml import etree
import xml.etree.ElementTree as ET
import base64
import logging

# Создание логгера для текущего модуля
_logger = logging.getLogger(__name__)

# Установка уровня логирования на DEBUG для вывода всех сообщений
_logger.setLevel(logging.DEBUG)

# Создание обработчика для вывода сообщений в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Определение формата сообщений
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Добавление обработчика к логгеру
_logger.addHandler(console_handler)


class BankStatImport(models.Model):
    _name = "bank.stat.import"
    _description = "bank stat import"

    name = fields.Char(string='Наименование')
    date = fields.Date(string='Дата')
    amount = fields.Float(string='Сумма')

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def create_document_from_attachment(self, attachment_ids):
        print("**create_document_from_attachment**")
        print("attachment_ids:", attachment_ids)

        attachments = self.env['ir.attachment'].browse(attachment_ids)
        for attachment in attachments:
            print("**attachment**")
            print("name:", attachment.name)

            content_data = base64.b64decode(attachment.datas)
            xml_etree = etree.fromstring(content_data)
            
            extractList_elems = xml_etree.find("{*}extractList")
            # print(extractList_elems)

            for turn in extractList_elems.findall("{*}turns"):
                crAmount = turn.find("{*}crAmount").text
                naznText = turn.find("{*}naznText").text
                # print("crAmount", crAmount, "naznText", naznText)

                payment_data = {
                    'amount': crAmount, 
                    'ref': naznText
                    }
                new_payment = self.env['account.payment'].create(payment_data)
                print("PAYMENT DATA", payment_data)
            
               


        return {}
