from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import CashRegisterSession, Transaction

class CashierService:
    """
    Centraliza todas as operações críticas de caixa.
    Nenhuma view deve mexer no saldo diretamente sem passar por aqui.
    """

    @staticmethod
    def open_session(user, opening_balance):
        """
        Abre um novo turno para o funcionário.
        """
        # 1. Verifica se já tem caixa aberto (Segurança)
        if CashRegisterSession.objects.filter(user=user, status=CashRegisterSession.Status.OPEN).exists():
            raise ValidationError("Você já possui um caixa aberto. Feche-o antes de abrir um novo.")

        # 2. Cria a sessão
        session = CashRegisterSession.objects.create(
            user=user,
            opening_balance=opening_balance,
            status=CashRegisterSession.Status.OPEN
        )
        return session

    @staticmethod
    def get_current_session(user):
        """
        Retorna o caixa aberto do usuário ou None.
        Útil para validar se ele pode receber pagamentos.
        """
        return CashRegisterSession.objects.filter(
            user=user,
            status=CashRegisterSession.Status.OPEN
        ).first()


    @staticmethod
    def register_consumption(booking, product, quantity, user):
        """
        Lança um consumo na conta.
        """
        if product.stock < quantity:
            raise ValidationError(f"Estoque insuficiente! Só restam {product.stock} unidades de {product.name}.")

        total_price = product.price * quantity

        # Usa a sessão do caixa atual (opcional, mas bom para rastreio)
        session = CashierService.get_current_session(user)

        # 1. Cria a Transação
        Transaction.objects.create(
            session=session,
            booking=booking,
            product=product, # Vincula o produto
            amount=total_price, # Valor POSITIVO (aumenta a conta)
            transaction_type=Transaction.Type.CONSUMPTION,
            payment_method=None, # Não é pagamento, é dívida
            description=f"Consumo: {quantity}x {product.name}"
        )

        # 2. Baixa o Estoque
        product.stock -= quantity
        product.save()



    @staticmethod
    def close_session(session, declared_balance, notes=""):
        """
        O Momento da Verdade (Fechamento de Caixa).
        Compara o que o sistema calculou com o que o funcionário diz ter na gaveta.
        """
        if session.status == CashRegisterSession.Status.CLOSED:
            raise ValidationError("Este caixa já foi fechado.")

        # 1. Calcula quanto o sistema acha que tem (Saldo Inicial + Entradas - Saídas)
        total_income = session.transactions.filter(
            transaction_type=Transaction.Type.INCOME
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        total_expenses = session.transactions.filter(
            transaction_type__in=[Transaction.Type.EXPENSE, Transaction.Type.REFUND]
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        # Nota: As despesas já são salvas negativas no banco, então somamos tudo
        # Mas por segurança, vamos garantir a matemática aqui:
        # Saldo Calculado = Inicial + (Soma de tudo)
        all_transactions_sum = session.transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        calculated_balance = session.opening_balance + all_transactions_sum

        # 2. Calcula a Diferença (Quebra de Caixa)
        # Ex: Sistema diz 1000. Funcionário conta 990. Diferença = -10.
        difference = Decimal(declared_balance) - calculated_balance

        # 3. Atualiza e Fecha a Sessão
        session.closing_balance = declared_balance # O que o funcionário contou
        session.calculated_balance = calculated_balance # O que devia ter
        session.difference = difference # O veredito
        session.closing_notes = notes
        session.closed_at = timezone.now()
        session.status = CashRegisterSession.Status.CLOSED
        session.save()

        return session

    @staticmethod
    def register_transaction(user, amount, transaction_type, method, description, booking=None):
        """
        Registra uma entrada/saída vinculada ao caixa do usuário logado.
        """
        session = CashierService.get_current_session(user)

        if not session:
            raise ValidationError("Você precisa abrir o caixa antes de realizar transações.")

        transaction = Transaction.objects.create(
            session=session,
            amount=amount,
            transaction_type=transaction_type,
            payment_method=method,
            description=description,
            booking=booking
        )
        return transaction
