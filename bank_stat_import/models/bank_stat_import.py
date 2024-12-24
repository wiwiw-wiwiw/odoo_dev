# -*- coding: utf-8 -*-
from odoo import models, api, fields
from .statement_parsers import BankStatementParser_BELBBY2X, BankStatementParser_AKBBBY2X
import base64
import logging

_logger = logging.getLogger(__name__)

class BankStatImport(models.TransientModel):
    """
    TransientModel для обработки импорта банковских выписок.
    
    Основные функции:
    - Чтение и обработка файлов банковских выписок
    - Пакетная обработка данных для минимизации запросов к БД
    - Создание и обновление связанных записей (партнеры, банки, счета)
    - Создание платежных записей на основе выписок
    """
    _name = 'bank.statement.import'
    _description = 'Bank Statement Import'

    def create_document_from_attachment(self, attachment_ids, parser_type):
        """
        Основной метод обработки файлов банковских выписок.
        
        Args:
            attachment_ids (list): Список ID вложений (ir.attachment)
            parser_type (str): Тип парсера ('BELBBY2X', 'AKBBBY2X')
        
        Returns:
            dict: Действие Odoo (уведомление о результате)
        
        Raises:
            ValueError: Если вложения не найдены или возникла ошибка при обработке
        """
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise ValueError("Вложения не найдены или отсутствуют.")

        # Словари для накопления данных из всех файлов
        all_transactions = []
        all_transaction_hashes = set()
        all_partners_data = {}
        all_banks_data = {}
        all_accounts_data = {}
        
        # Обработка каждого вложения
        for attachment in attachments:
            try:
                # Получение и декодирование содержимого файла
                content_data = base64.b64decode(attachment.datas)
                parser = self._get_parser(parser_type)
                
                # Парсинг данных из файла
                transactions_dict, transaction_hashes, partners_data, banks_data, accounts_data = (
                    parser.parse_and_process(content_data)
                )
                
                # Фильтрация дубликатов транзакций
                filtered_transactions = self._filter_transactions(transactions_dict, transaction_hashes)
                
                if filtered_transactions:
                    all_transactions.extend(filtered_transactions)
                    all_transaction_hashes.update(transaction_hashes)
                    all_partners_data.update(partners_data)
                    all_banks_data.update(banks_data)
                    all_accounts_data.update(accounts_data)
                
                _logger.info(f"Файл {attachment.name} успешно обработан")
                
            except Exception as e:
                _logger.error(f"Ошибка обработки файла {attachment.name}: {str(e)}")
                raise ValueError(f"Ошибка обработки файла {attachment.name}: {str(e)}")

        if not all_transactions:
            return self._notify("Файлы не содержат новых транзакций.", 'warning')

        # Пакетная обработка всех связанных данных
        partner_mapping = self._process_partners_batch(all_partners_data)
        bank_mapping = self._process_banks_batch(all_banks_data)
        account_mapping = self._process_accounts_batch(all_accounts_data, partner_mapping, bank_mapping)
        
        # Создание платежей
        self._create_payments_from_transactions(all_transactions, partner_mapping, account_mapping)
        
        return self._notify("Импорт завершён успешно.", 'success')

    def _get_parser(self, parser_type):
        """
        Возвращает соответствующий парсер на основе типа.
        
        Args:
            parser_type (str): Тип парсера
        
        Returns:
            object: Экземпляр класса парсера
            
        Raises:
            ValueError: Если тип парсера не поддерживается
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
        Фильтрует транзакции, исключая существующие в системе.
        
        Args:
            transactions_dict (dict): Словарь транзакций
            transaction_hashes (set): Множество хэшей транзакций
        
        Returns:
            list: Список новых транзакций
        """
        existing_hashes = set(self.env['account.payment'].search([
            ('transaction_hash', 'in', list(transaction_hashes))
        ]).mapped('transaction_hash'))
        
        return [
            transaction 
            for hash_key, transaction in transactions_dict.items() 
            if hash_key not in existing_hashes
        ]

    def _process_partners_batch(self, partners_data):
        """
        Пакетная обработка данных партнеров.
        
        Args:
            partners_data (dict): Словарь с данными партнеров
        
        Returns:
            dict: Маппинг имен партнеров на их записи
        """
        # Получаем существующих партнеров одним запросом
        existing_partners = self.env['res.partner'].search([
            ('name', 'in', list(partners_data.keys()))
        ])
        partner_mapping = {partner.name: partner for partner in existing_partners}
        
        # Создаем отсутствующих партнеров
        partners_to_create = [
            {'name': name}
            for name in partners_data
            if name not in partner_mapping
        ]
        
        if partners_to_create:
            new_partners = self.env['res.partner'].create(partners_to_create)
            partner_mapping.update({partner.name: partner for partner in new_partners})
        
        return partner_mapping

    def _process_banks_batch(self, banks_data):
        """
        Пакетная обработка данных банков.
        
        Args:
            banks_data (dict): Словарь с данными банков
        
        Returns:
            dict: Маппинг BIC банков на их записи
        """
        existing_banks = self.env['res.bank'].search([
            ('bic', 'in', list(banks_data.keys()))
        ])
        bank_mapping = {bank.bic: bank for bank in existing_banks}
        
        banks_to_create = [
            {'name': data['name'], 'bic': bic}
            for bic, data in banks_data.items()
            if bic not in bank_mapping
        ]
        
        if banks_to_create:
            new_banks = self.env['res.bank'].create(banks_to_create)
            bank_mapping.update({bank.bic: bank for bank in new_banks})
        
        return bank_mapping

    def _process_accounts_batch(self, accounts_data, partner_mapping, bank_mapping):
        """
        Пакетная обработка банковских счетов.
        
        Args:
            accounts_data (dict): Словарь с данными счетов
            partner_mapping (dict): Маппинг партнеров
            bank_mapping (dict): Маппинг банков
        
        Returns:
            dict: Маппинг номеров счетов на их записи
        """
        existing_accounts = self.env['res.partner.bank'].search([
            ('acc_number', 'in', list(accounts_data.keys()))
        ])
        account_mapping = {account.acc_number: account for account in existing_accounts}
        
        accounts_to_create = []
        for acc_num, data in accounts_data.items():
            if acc_num in account_mapping:
                continue
                
            partner = partner_mapping.get(data['partner_name'])
            if not partner:
                continue
                
            accounts_to_create.append({
                'acc_number': acc_num,
                'partner_id': partner.id,
                'bank_id': bank_mapping.get(data.get('bank_bic')).id if data.get('bank_bic') else False,
            })
        
        if accounts_to_create:
            new_accounts = self.env['res.partner.bank'].create(accounts_to_create)
            account_mapping.update({account.acc_number: account for account in new_accounts})
        
        return account_mapping

    def _create_payments_from_transactions(self, transactions, partner_mapping, account_mapping):
        """
        Пакетное создание платежей из транзакций.
        """
        # Фильтруем транзакции с существующими партнерами и счетами
        valid_transactions = [
            t for t in transactions
            if partner_mapping.get(t['partner_name']) and 
            account_mapping.get(t.get('partner_account', ''))
        ]
        
        # Логируем пропущенные транзакции
        skipped = set(t['partner_name'] for t in transactions) - set(t['partner_name'] for t in valid_transactions)
        if skipped:
            _logger.warning(f"Пропущены транзакции для партнеров: {', '.join(skipped)}")
        
        # Создаем все платежи одной операцией
        payment_data = [{
            'amount': t['amount'],
            'payment_type': t['payment_type'],
            'ref': t['reference'],
            'date': t['date'],
            'partner_id': partner_mapping[t['partner_name']].id,
            'partner_bank_id': account_mapping[t.get('partner_account', '')].id,
            'transaction_hash': t['transaction_hash'],
        } for t in valid_transactions]
        
        if payment_data:
            self.env['account.payment'].create(payment_data)

    def _notify(self, message, message_type):
        """
        Создает уведомление для интерфейса Odoo.
        
        Args:
            message (str): Текст уведомления
            message_type (str): Тип уведомления ('success', 'warning', 'error')
        
        Returns:
            dict: Действие клиента Odoo
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