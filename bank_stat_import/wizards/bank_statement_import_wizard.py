# bank_statement_import/models/bank_statement_import_wizard.py


# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64

class BankStatementImportWizard(models.TransientModel):
    _name = 'bank.statement.import.wizard'
    _description = 'Bank Statement Import Wizard'

    bank_parser = fields.Selection([
        ('BELBBY2X', 'ОАО "Банк БелВЭБ"'),
        ('AKBBBY2X', 'АСБ Беларусбанк'),
    ], string='Банк', required=True)
    file = fields.Binary('Файл', required=True, help="Загрузите файл банковской выписки.")
    file_name = fields.Char('Имя файла')

    def action_import(self):
        """
        Запуск импорта банковской выписки.
        
        Входные данные:
        - bank_parser: Тип парсера (например, 'BELBBY2X').
        - file: Бинарное содержимое файла в формате Base64.
        - file_name: Имя файла.

        Пример формата файла:
        - См. документацию классов парсеров.

        Выходные данные:
        - Созданные платежи.
        - Уведомление об успехе или ошибке.
        """
        if not self.file:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка',
                    'message': 'Файл не загружен.',
                    'type': 'danger',
                },
            }

        # Сохранение файла во вложения
        attachment = self.env['ir.attachment'].create({
            'name': self.file_name or f"bank_statement_{fields.Datetime.now()}.xml",
            'type': 'binary',
            'datas': self.file,
            'res_model': self._name,
            'res_id': self.id,
        })

        # Импорт через модель `bank.statement.import`
        try:
            self.env['bank.statement.import'].create_document_from_attachment(
                [attachment.id],
                self.bank_parser
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Успешно',
                    'message': 'Файл успешно импортирован.',
                    'type': 'success',
                },
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка импорта',
                    'message': f'Произошла ошибка: {str(e)}',
                    'type': 'danger',
                },
            }
