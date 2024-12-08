# bank_statement_import/models/bank_stat_import.py
# -*- coding: utf-8 -*-
from odoo import models, api, fields
from .statement_parsers import BankStatementParser_BELBBY2X, BankStatementParser_AKBBBY2X
import base64
import logging

_logger = logging.getLogger(__name__)

class BankStatImport(models.TransientModel):
    """
    TransientModel для обработки импорта банковских выписок.
    Отвечает за чтение вложенных файлов, выбор парсера,
    обработку транзакций и создание платежных записей.
    """
    _name = 'bank.statement.import'
    _description = 'Bank Statement Import'

    def create_document_from_attachment(self, attachment_ids, parser_type):
        """
        Обрабатывает файл банковской выписки и создает записи платежей.
        
        :param attachment_ids: Список ID вложений (ir.attachment)
        :param parser_type: Тип парсера ('BELBBY2X', 'AKBBBY2X')
        :return: Действие открытия созданных платежей или уведомление
        """
        attachments = self.env['ir.attachment'].browse(attachment_ids)

        # Проверка на наличие вложений
        if not attachments:
            raise ValueError("Вложения не найдены или отсутствуют.")

        for attachment in attachments:
            # Логика выбора парсера
            parser = self._get_parser(parser_type)

            # Декодирование содержимого файла
            try:
                content_data = base64.b64decode(attachment.datas)
                _logger.info("Файл %s успешно декодирован", attachment.name)
            except Exception as e:
                _logger.error("Ошибка декодирования файла %s: %s", attachment.name, str(e))
                raise ValueError("Ошибка декодирования файла.")

            # Парсинг транзакций с хэшами и дополнительными данными
            transactions_dict, transaction_hashes, partners_data, banks_data, accounts_data = parser.parse_and_process(content_data)
        
            # Фильтрация дубликатов транзакций
            filtered_transactions = self._filter_transactions(transactions_dict, transaction_hashes)
        
            if not filtered_transactions:
                _logger.warning("Файл %s не содержит новых транзакций", attachment.name)
                return self._notify("Файл не содержит новых транзакций.", 'warning')

            # Фильтрация и создание партнеров, банков, счетов
            filtered_partners = self._filter_partners(partners_data)
            filtered_banks = self._filter_banks(banks_data)
            filtered_accounts = self._filter_accounts(accounts_data, filtered_partners)
            
            # Создание отсутствующих записей
            created_partners = self._create_missing_partners(filtered_partners)
            created_banks = self._create_missing_banks(filtered_banks)
            created_accounts = self._create_missing_accounts(filtered_accounts, created_partners, created_banks)

            # Создание платежей
            self._create_payments_from_transactions(filtered_transactions)

        return self._notify("Импорт завершён успешно.", 'success')

    def _get_parser(self, parser_type):
        """
        Возвращает парсер на основе переданного типа.
        """
        parsers = {
            'BELBBY2X': BankStatementParser_BELBBY2X,
            'AKBBBY2X': BankStatementParser_AKBBBY2X,
        }
        parser_class = parsers.get(parser_type)
        if not parser_class:
            raise ValueError(f"Неподдерживаемый тип парсера: {parser_type}")
        return parser_class()

    def _filter_transactions(self, transactions_dict, transaction_hashes):
        """
        Фильтрация транзакций, исключая уже существующие в account.payments.
        
        :param transactions_dict: Словарь транзакций с хэшами в качестве ключей
        :param transaction_hashes: Список хэшей транзакций
        :return: Список словарей новых транзакций, готовых к загрузке
        """
        existing_hashes = self.env['account.payment'].search([
            ('transaction_hash', 'in', transaction_hashes)
        ]).mapped('transaction_hash')
    
        filtered_transactions = [
            transaction 
            for hash_key, transaction in transactions_dict.items() 
            if hash_key not in existing_hashes
        ]

        return filtered_transactions

    def _filter_partners(self, partners_data):
        """
        Фильтрация партнеров, которые еще не существуют в базе.
        """
        existing_partners = self.env['res.partner'].search([
            ('name', 'in', list(partners_data.keys()))
        ])
        existing_partner_names = existing_partners.mapped('name')
        
        return {
            name: data 
            for name, data in partners_data.items() 
            if name not in existing_partner_names
        }

    def _filter_banks(self, banks_data):
        """
        Фильтрация банков, которые еще не существуют в базе.
        """
        existing_banks = self.env['res.bank'].search([
            ('bic', 'in', [data['bic'] for data in banks_data.values()])
        ])
        existing_bank_codes = existing_banks.mapped('bic')
        
        return {
            bic: data 
            for bic, data in banks_data.items() 
            if bic not in existing_bank_codes
        }

    def _filter_accounts(self, accounts_data, filtered_partners):
        """
        Фильтрация банковских счетов, которые еще не существуют в базе.
        """
        existing_accounts = self.env['res.partner.bank'].search([
            ('acc_number', 'in', [data['acc_number'] for data in accounts_data.values()])
        ])
        existing_account_numbers = existing_accounts.mapped('acc_number')
        
        return {
            acc_num: data 
            for acc_num, data in accounts_data.items() 
            if acc_num not in existing_account_numbers and data['partner_name'] not in filtered_partners
        }

    def _create_missing_partners(self, partners):
        """
        Создание новых партнеров.
        """
        if not partners:
            return {}
        
        created_partners = self.env['res.partner'].create([
            {'name': name} for name in partners.keys()
        ])
        
        return {partner.name: partner for partner in created_partners}

    def _create_missing_banks(self, banks):
        """
        Создание новых банков.
        """
        if not banks:
            return {}
        
        created_banks = self.env['res.bank'].create([
            {'name': data['name'], 'bic': bic} 
            for bic, data in banks.items()
        ])
        
        return {bank.bic: bank for bank in created_banks}

    def _create_missing_accounts(self, accounts, created_partners, created_banks):
            """
            Создание новых банковских счетов.
            """
            if not accounts:
                return {}
            
            accounts_to_create = []
            for acc_num, data in accounts.items():
                partner = created_partners.get(data['partner_name'])
                if partner:
                    accounts_to_create.append({
                        'acc_number': acc_num,
                        'partner_id': partner.id,
                    })
            
            if accounts_to_create:
                created_accounts = self.env['res.partner.bank'].create(accounts_to_create)
                return {account.acc_number: account for account in created_accounts}
            
            return {}

    def _create_payments_from_transactions(self, transactions):
        """
        Создание платежей из отфильтрованных транзакций.
        
        :param transactions: Список транзакций для создания
        """
        if not transactions:
            return
        
        payment_data = []
        for transaction in transactions:
            partner = self.env['res.partner'].search([('name', '=', transaction['partner_name'])], limit=1)
            partner_bank = self.env['res.partner.bank'].search([
                ('acc_number', '=', transaction.get('partner_account', '')), 
                ('partner_id', '=', partner.id)
            ], limit=1)

            payment_data.append({
                'amount': transaction['amount'],
                'payment_type': transaction['payment_type'],
                'ref': transaction['reference'],
                'date': transaction['date'],
                'partner_id': partner.id,
                'partner_bank_id': partner_bank.id,
                'transaction_hash': transaction['transaction_hash'],
            })
        
        if payment_data:
            self.env['account.payment'].create(payment_data)

    def _notify(self, message, message_type):
        """
        Генерирует уведомление для интерфейса Odoo.
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Уведомление',
                'message': message,
                'type': message_type,
                'sticky': False,
            },
        }





   