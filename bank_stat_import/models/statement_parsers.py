# bank_statement_import/models/statement_parsers.py
# -*- coding: utf-8 -*-
from lxml import etree
from datetime import datetime
import logging
import hashlib

_logger = logging.getLogger(__name__)

class BaseStatementParser:
    """
    Базовый класс парсера банковской выписки с универсальным методом парсинга и обработки транзакций.
    """
    def parse_and_process(self, content):
        """
        Универсальный метод для парсинга и обработки транзакций за один проход.
        
        :param content: Данные файла в формате строки (например, XML)
        :return: Кортеж (словарь транзакций с хэшами, список хэшей, партнеры, банки, счета)
        """
        raise NotImplementedError("Подклассы должны реализовать этот метод")
    
    def _generate_transaction_hash(self, transaction):
        """
        Генерация хэша для транзакции.
        
        :param transaction: Словарь с данными транзакции
        :return: Хэш транзакции
        """
        hash_string = f"{transaction['date']}|{transaction['amount']}|{transaction['reference']}"
        return hashlib.sha256(hash_string.encode()).hexdigest()


class BankStatementParser_BELBBY2X(BaseStatementParser):
    def parse_and_process(self, content):
        xml_etree = etree.fromstring(content)
        transactions_dict = {}
        transaction_hashes = []
        
        # Словари для сбора уникальных партнеров, банков и счетов
        partners_data = {}
        banks_data = {}
        accounts_data = {}
        
        extract_list_elems = xml_etree.find("{*}extractList")
        if extract_list_elems is not None:
            for turn in extract_list_elems.findall("{*}turns"):
                # определение типа транзакции
                db_amount = turn.findtext("{*}dbAmount") or '0'
                cr_amount = turn.findtext("{*}crAmount") or '0'
                # определение типа транзакции по наличию суммы
                if float(db_amount) > 0:
                    payment_type = 'outbound'
                    amount = db_amount
                elif float(cr_amount) > 0:
                    payment_type = 'inbound'
                    amount = cr_amount
                else:
                    # пропускаем транзакции с нулевой суммой
                    continue
                
                transaction = {
                    'date': datetime.strptime(turn.findtext("{*}docDate"), "%Y-%m-%dT%H:%M:%S%z").date() if turn.findtext("{*}docDate") else None,
                    'amount': amount,
                    'payment_type': payment_type,
                    'partner_name': turn.findtext("{*}corrName") or '',
                    'partner_account': turn.findtext("{*}corrAccount") or '',
                    'partner_bank_code': turn.findtext("{*}corrBankCode") or '',
                    'partner_bank_name': turn.findtext("{*}corrBankName") or '',
                    'reference': turn.findtext("{*}naznText") or '',
                }
                
                transaction_hash = self._generate_transaction_hash(transaction)
                transaction['transaction_hash'] = transaction_hash
                
                transactions_dict[transaction_hash] = transaction
                transaction_hashes.append(transaction_hash)
                
                # Сбор уникальных данных о партнерах, банках и счетах
                if transaction['partner_name']:
                    partners_data[transaction['partner_name']] = {
                        'name': transaction['partner_name']
                    }
                
                if transaction['partner_bank_code']:
                    banks_data[transaction['partner_bank_code']] = {
                        'bic': transaction['partner_bank_code'],
                        'name': transaction['partner_bank_name'] or transaction['partner_bank_code']
                    }
                
                if transaction['partner_account']:
                    accounts_data[transaction['partner_account']] = {
                        'acc_number': transaction['partner_account'],
                        'partner_name': transaction['partner_name']
                    }
        
        return transactions_dict, transaction_hashes, partners_data, banks_data, accounts_data


class BankStatementParser_AKBBBY2X(BaseStatementParser):
    def parse_and_process(self, content):
        xml_etree = etree.fromstring(content)
        transactions_dict = {}
        transaction_hashes = []
        
        # Словари для сбора уникальных партнеров, банков и счетов
        partners_data = {}
        banks_data = {}
        accounts_data = {}
        
        for account_info in xml_etree.findall('.//ACCOUNTINFO'):
            currency = account_info.find('CURRENCY').get('Iso')
            date = account_info.find('TIMETURN').get('date')

            for oper in account_info.findall('.//OPER'):
                # Определение типа платежа и суммы
                payment_type = 'outbound' if float(oper.find('SUMOPER').get('nd') or 0) > 0 else 'inbound'
                amount = float(oper.find('SUMOPER').get('nd') if payment_type == 'outbound' else oper.find('SUMOPER').get('nk') or '0')
                
                # Парсинг и преобразование транзакции
                transaction = {
                    'date': datetime.strptime(date, "%d.%m.%Y").date() if date else None,
                    'payment_type': payment_type,
                    'amount': amount,
                    'partner_name': oper.findtext('NAMEKORR') or '',
                    'partner_account': oper.findtext('ACCKORR') or '',
                    'partner_bank_code': oper.findtext('MFOKORR') or '',
                    'partner_bank_name': '',
                    'reference': oper.findtext('DETPAY') or '',
                    'currency': currency,
                }
                
                # Генерация хэша
                transaction_hash = self._generate_transaction_hash(transaction)
                transaction['transaction_hash'] = transaction_hash
                
                transactions_dict[transaction_hash] = transaction
                transaction_hashes.append(transaction_hash)
                
                # Сбор уникальных данных о партнерах, банках и счетах
                if transaction['partner_name']:
                    partners_data[transaction['partner_name']] = {
                        'name': transaction['partner_name']
                    }
                
                if transaction['partner_bank_code']:
                    banks_data[transaction['partner_bank_code']] = {
                        'bic': transaction['partner_bank_code'],
                        'name': transaction.get('partner_bank_name') or transaction['partner_bank_code']
                    }
                
                if transaction['partner_account']:
                    accounts_data[transaction['partner_account']] = {
                        'acc_number': transaction['partner_account'],
                        'partner_name': transaction['partner_name']
                    }
        
        return transactions_dict, transaction_hashes, partners_data, banks_data, accounts_data