from odoo import models, fields, api
import base64
from lxml import etree


class BankStatImport(models.Model):
    _name = "bank.stat.import"
    _description = "bank stat import"

    name = fields.Char(string='Наименование')
    date = fields.Date(string='Дата')
    amount = fields.Float(string='Сумма')


    def create_document_from_attachment(self, attachment_ids):
        print("**create_document_from_attachment**")
        print("attachment_ids:", attachment_ids)

        attachments = self.env['ir.attachment'].browse(attachment_ids)
        for attachment in attachments:
            print("**attachment**")
            print("name:", attachment.name)
            # print("datas:", attachment.datas)

            file_name = attachment.name
            base64_data = attachment.datas
            bytes_content = base64.b64decode(base64_data)

            # Декодируем байты напрямую в строку (без лишнего кодирования)
            string_content = bytes_content.decode("utf-8")
            print("string_content", string_content)
            # Парсим XML-строку с помощью lxml.etree.fromstring
            xml_tree = etree.fromstring(string_content)
            print(xml_tree)

            # **Вставьте здесь код обработки XML-данных**

        return {}

