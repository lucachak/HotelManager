import os
import random
from datetime import timedelta
from decimal import Decimal

import django
from django.utils import timezone
from django.utils.text import slugify

# 1. Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.accommodations.models import Room, RoomCategory
from apps.bookings.models import Booking, RoomAllocation
# 2. Importar os modelos
from apps.core.models import User
from apps.financials.models import (CashRegisterSession, PaymentMethod,
                                    Product, Transaction)
from apps.guests.models import Guest


def get_field_name(model, possibilities):
    """Função auxiliar para encontrar o nome correto do campo no modelo."""
    model_fields = [f.name for f in model._meta.get_fields()]
    for field in possibilities:
        if field in model_fields:
            return field
    return possibilities[0] 

def seed_data():
    print("🌱 A iniciar a população da base de dados (Seed)...")

    # ---------------------------------------------------------
    # 1. UTILIZADORES
    # ---------------------------------------------------------
    print("👤 A criar utilizadores...")
    users_data = [
        {'email': 'admin@hotel.com', 'name': 'Administrador Sistema', 'role': 'MANAGER'},
        {'email': 'recepcao@hotel.com', 'name': 'Ana Rececionista', 'role': 'RECEPTIONIST'},
    ]
    
    for u_data in users_data:
        if not User.objects.filter(email=u_data['email']).exists():
            names = u_data['name'].split(' ', 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ''

            User.objects.create_user(
                email=u_data['email'],
                password='admin',
                first_name=first_name,
                last_name=last_name,
                role=u_data['role'],
                is_staff=True,
                is_superuser=(u_data['role'] == 'MANAGER')
            )
            print(f"   ✅ Utilizador criado: {u_data['email']} (Senha: admin)")

    manager_user = User.objects.filter(role='MANAGER').first() or User.objects.first()

    # ---------------------------------------------------------
    # 2. FINANCEIRO
    # ---------------------------------------------------------
    print("💳 A configurar financeiro...")
    methods = ['Dinheiro', 'Multibanco', 'Cartão de Crédito', 'MB Way']
    for m in methods:
        PaymentMethod.objects.update_or_create(
            name=m,
            defaults={'slug': slugify(m), 'is_active': True}
        )

    print("🥤 A preencher o stock do frigobar...")
    products = [
        ('Água Mineral 500ml', '1.50'),
        ('Coca-Cola Lata', '2.50'),
        ('Cerveja Super Bock', '3.00'),
        ('Batatas Pringles', '4.00'),
        ('Chocolate Snickers', '2.00'),
        ('Vinho Tinto 375ml', '12.00')
    ]
    for name, price in products:
        Product.objects.update_or_create(
            name=name,
            defaults={'price': Decimal(price), 'stock': random.randint(10, 50), 'is_active': True}
        )

    # ---------------------------------------------------------
    # 3. ALOJAMENTO
    # ---------------------------------------------------------
    print("🏨 A construir quartos...")
    price_field = get_field_name(RoomCategory, ['base_price', 'daily_rate', 'price', 'price_per_day'])
    
    cats = [
        {'name': 'Standard', 'price': '80.00'},
        {'name': 'Vista Mar', 'price': '120.00'},
        {'name': 'Suite Luxo', 'price': '250.00'},
    ]

    for c in cats:
        cat_obj, _ = RoomCategory.objects.update_or_create(
            name=c['name'],
            defaults={price_field: Decimal(c['price'])}
        )
        
        start_num = 100 if c['name'] == 'Standard' else (200 if c['name'] == 'Vista Mar' else 300)
        for i in range(1, 6):
            room_num = str(start_num + i)
            if not Room.objects.filter(number=room_num).exists():
                Room.objects.create(
                    number=room_num,
                    category=cat_obj,
                    status='AVAILABLE'
                )

    # ---------------------------------------------------------
    # 4. HÓSPEDES
    # ---------------------------------------------------------
    print("👥 A registar hóspedes...")
    guests_list = [
        ('João Silva', '123456789', 'joao@email.com'),
        ('Maria Santos', '987654321', 'maria@email.com'),
        ('Pedro Costa', '456123789', 'pedro@email.com'),
        ('Ana Pereira', '789123456', 'ana@email.com'),
        ('Carlos Ferreira', '321654987', 'carlos@email.com'),
    ]

    created_guests = []
    for name, doc, email in guests_list:
        guest, _ = Guest.objects.update_or_create(
            email=email,
            defaults={
                'name': name,
                'document': doc,
                'phone': f'+351 910 000 {random.randint(100, 999)}'
            }
        )
        created_guests.append(guest)

    # ---------------------------------------------------------
    # 5. HISTÓRICO E RESERVAS
    # ---------------------------------------------------------
    print("💰 A gerar histórico financeiro e reservas...")
    
    pay_method = PaymentMethod.objects.first()
    today = timezone.now()
    session_open_field = get_field_name(CashRegisterSession, ['opened_at', 'created_at', 'start_time'])
    rooms = list(Room.objects.all())
    
    for i in range(7, -1, -1):
        day = today - timedelta(days=i)
        is_past = (i > 0)
        
        # Estratégia: Criar sempre ABERTO primeiro para permitir transações
        session_data = {
            'user': manager_user,
            'opening_balance': Decimal('150.00'),
            'status': 'OPEN', # Forçamos OPEN inicialmente
            'closed_at': (day + timedelta(hours=10)) if is_past else None,
            'calculated_balance': Decimal('150.00'),
            session_open_field: day
        }
        
        if i == 0:
             session = CashRegisterSession.objects.filter(status='OPEN').first()
             if not session:
                 session = CashRegisterSession.objects.create(**session_data)
        else:
             session = CashRegisterSession.objects.create(**session_data)

        # Inserir transações enquanto está ABERTO
        if is_past:
            income = Decimal(random.randint(200, 800))
            Transaction.objects.create(
                session=session,
                amount=income,
                transaction_type='INCOME',
                payment_method=pay_method,
                description=f"Receita do dia {day.strftime('%d/%m')}"
            )
            
            # Agora sim, FECHAR a sessão
            session.closing_balance = session.opening_balance + income
            session.calculated_balance = session.closing_balance
            session.status = 'CLOSED'
            session.save()

        # Criar reservas
        if i < 5 and rooms:
            guest = random.choice(created_guests)
            room = rooms[i % len(rooms)]
            check_in = day
            check_out = day + timedelta(days=random.randint(1, 3))
            status = 'CHECKED_IN' if check_out > today else 'COMPLETED'
            
            try:
                if not Booking.objects.filter(guest=guest, created_at__date=day.date()).exists():
                    booking = Booking.objects.create(
                        guest=guest,
                        status=status,
                        notes="Reserva automática"
                    )
                    
                    RoomAllocation.objects.create(
                        booking=booking,
                        room=room,
                        check_in=check_in,
                        check_out=check_out
                    )
                    
                    if status == 'CHECKED_IN':
                        room.status = 'OCCUPIED'
                        room.save()
                        
                    print(f"   📅 Reserva: {guest.name} -> Quarto {room.number}")
            except Exception:
                pass

    print("\n✅ Concluído! Login: admin@hotel.com / admin")

if __name__ == '__main__':
    seed_data()
