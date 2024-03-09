# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
from lxml import etree
import xml.etree.ElementTree as ET


class BankStatImport(models.Model):
    _name = "bank.stat.import"
    _description = "bank stat import"

    name = fields.Char(string='Наименование')
    date = fields.Date(string='Дата')
    amount = fields.Float(string='Сумма')

   
class MyModuleParser:
    def parse_file(self, file_content):
        root = ET.fromstring(file_content)



def create_document_from_attachment(self, attachment_ids):
        print("attachment_ids", attachment_ids)
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        print("attachments", attachments)
        for attachment in attachments:
            file_name = attachment.name
            base64_data = attachment.datas
            bytes_content = base64.b64decode(base64_data)
            string_context = bytes_content.decode("utf-8")
            xml_tree = etree.fromstring(string_context.encode("utf-8"))
#             # print("file_name", file_name)
#             # print("base64_data", base64_data)
#             # print("bytes", bytes_content)
#             # print("string_context", string_context)
            print("xml_tree", xml_tree)

