from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
# Importação relativa funciona bem aqui dentro do mesmo app
from .models import Booking, RoomAllocation 

def create_booking_safely(guest, room, start_date, end_date, user):
    """
    Cria uma reserva com TRAVAMENTO DE BANCO DE DADOS (Atomicidade).
    Isso impede que dois usuários reservem o mesmo quarto ao mesmo tempo.
    """
    
    # Validação básica de datas (regra de negócio)
    if start_date >= end_date:
        raise ValidationError("A data de saída deve ser posterior à data de entrada.")

    # Inicia uma transação atômica (Tudo ou Nada)
    with transaction.atomic():
        # 1. Verifica disponibilidade TRAVANDO as linhas afetadas no banco
        # O select_for_update() diz ao Postgres: "Ninguém mexe nessas linhas até eu terminar"
        # Isso é a proteção contra Race Conditions.
        conflicts = RoomAllocation.objects.select_for_update().filter(
            room=room,
            start_date__lt=end_date,  # Começa antes de eu sair
            end_date__gt=start_date   # Termina depois de eu chegar
        ).exclude(booking__status=Booking.Status.CANCELED)

        if conflicts.exists():
            raise ValidationError(f"O Quarto {room.number} acabou de ser ocupado por outra pessoa nestas datas.")

        # 2. Cria a Reserva Pai (O Contrato)
        booking = Booking.objects.create(
            guest=guest,
            status=Booking.Status.PENDING, # Começa pendente até pagar
            # Se quisermos registrar quem criou, podemos adicionar um campo 'created_by' no model depois
        )

        # 3. Cria a Alocação (A Ocupação Física)
        allocation = RoomAllocation.objects.create(
            booking=booking,
            room=room,
            start_date=start_date,
            end_date=end_date,
            # Se não passar preço, o model já pega o preço base do quarto no save()
        )

        return booking
