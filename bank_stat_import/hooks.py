# bank_statement_import/hooks.py
def post_init_hook(cr, registry):
    """
    Хук, выполняющийся после установки модуля.
    Вычисляет хэши для существующих записей в account.payment и сохраняет их.
    """
    from odoo.api import Environment
    
    env = Environment(cr, registry)
    payments = env['account.payment'].search([])
    
    for payment in payments:
        # Проверяем наличие уже существующего хэша, чтобы избежать дублирования
        if not payment.transaction_hash:
            transaction_hash = env['account.payment']._generate_transaction_hash(
                payment.date, 
                payment.amount, 
                payment.ref
            )
            payment.write({'transaction_hash': transaction_hash})
