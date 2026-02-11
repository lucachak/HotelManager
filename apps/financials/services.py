from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import CashRegisterSession, Transaction

class CashierService:
    @staticmethod
    def open_session(user, opening_balance):
        if CashRegisterSession.objects.filter(user=user, status=CashRegisterSession.Status.OPEN).exists():
            raise ValidationError("Você já possui um caixa aberto.")

        return CashRegisterSession.objects.create(
            user=user,
            opening_balance=opening_balance,
            status=CashRegisterSession.Status.OPEN
        )

    @staticmethod
    def get_current_session(user):
        return CashRegisterSession.objects.filter(
            user=user,
            status=CashRegisterSession.Status.OPEN
        ).first()

    @staticmethod
    def close_session(session, declared_balance, notes=""):
        if session.status == CashRegisterSession.Status.CLOSED:
            raise ValidationError("Este caixa já foi fechado.")

        all_transactions_sum = session.transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        calculated_balance = session.opening_balance + all_transactions_sum

        session.closing_balance = declared_balance
        session.calculated_balance = calculated_balance
        session.difference = Decimal(declared_balance) - calculated_balance
        session.closing_notes = notes
        session.closed_at = timezone.now()
        session.status = CashRegisterSession.Status.CLOSED
        session.save()
        return session

    @staticmethod
    def register_transaction(user, amount, transaction_type, method, description, booking=None):
        session = CashierService.get_current_session(user)
        if not session:
            raise ValidationError("Você precisa abrir o caixa antes de realizar transações.")

        return Transaction.objects.create(
            session=session,
            amount=amount,
            transaction_type=transaction_type,
            payment_method=method,
            description=description,
            booking=booking
        )

    @staticmethod
    def register_consumption(booking, product, quantity, user):
        """
        Lança consumo e baixa estoque.
        """
        if product.stock < quantity:
            raise ValidationError(f"Estoque insuficiente! Só restam {product.stock} unidades.")

        total_price = product.price * quantity
        session = CashierService.get_current_session(user)

        # Cria Transação
        Transaction.objects.create(
            session=session,
            booking=booking,
            product=product,
            amount=total_price,
            transaction_type=Transaction.Type.CONSUMPTION,
            payment_method=None,
            description=f"Consumo: {quantity}x {product.name}"
        )

        # Baixa Estoque
        product.stock -= quantity
        product.save()
