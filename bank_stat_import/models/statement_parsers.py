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
        :return: Кортеж (словарь транзакций с хэшами, список хэшей)
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
        
        extract_list_elems = xml_etree.find("{*}extractList")
        if extract_list_elems is not None:
            for turn in extract_list_elems.findall("{*}turns"):
                # Парсинг и преобразование транзакции
                transaction = {
                    'date': datetime.strptime(turn.findtext("{*}docDate"), "%Y-%m-%dT%H:%M:%S%z").date() if turn.findtext("{*}docDate") else None,
                    'amount': float(turn.findtext("{*}dbAmount") if turn.findtext("{*}turnType") == "DEBET" else turn.findtext("{*}crAmount") or '0'),
                    'payment_type': 'outbound' if turn.findtext("{*}turnType") == "DEBET" else 'inbound',
                    'partner_name': turn.findtext("{*}corrName") or '',
                    'partner_account': turn.findtext("{*}corrAccount") or '',
                    'partner_bank_code': turn.findtext("{*}corrBankCode") or '',
                    'partner_bank_name': turn.findtext("{*}corrBankName") or '',
                    'reference': turn.findtext("{*}naznText") or '',
                }
                
                # Генерация хэша
                transaction_hash = self._generate_transaction_hash(transaction)
                transaction['transaction_hash'] = transaction_hash
                
                transactions_dict[transaction_hash] = transaction
                transaction_hashes.append(transaction_hash)
        
        return transactions_dict, transaction_hashes


class BankStatementParser_AKBBBY2X(BaseStatementParser):
    def parse_and_process(self, content):
        xml_etree = etree.fromstring(content)
        transactions_dict = {}
        transaction_hashes = []
        
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
        
        return transactions_dict, transaction_hashes