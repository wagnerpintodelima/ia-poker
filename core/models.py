from django.db import models
import uuid

class Authorization(models.Model):
    level = models.CharField(max_length=100)    
    secret_key = models.CharField(max_length=64, unique=True, editable=False)    

    class Meta:
        db_table = 'authorization'  # <- Nome personalizado da tabela
    
    def save(self, *args, **kwargs):
        if not self.secret_key:
            self.secret_key = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(null=False, blank=False, default='player@iapoker.com', unique=True)
    callback_url = models.URLField()
    secret_key = models.CharField(max_length=64, unique=True, editable=False)
    is_bot = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    avatar_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'player'  # <- Nome personalizado da tabela
    
    def save(self, *args, **kwargs):
        if not self.secret_key:
            self.secret_key = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    
class Table(models.Model):
    name = models.CharField(max_length=100)
    max_players = models.PositiveIntegerField(default=6)
    initial_chips = models.PositiveIntegerField(default=1000)

    small_blind = models.PositiveIntegerField(default=10)
    big_blind = models.PositiveIntegerField(default=20)

    BLIND_STRATEGY_CHOICES = [
        ('fixed', 'Fixo'),
        ('timer', 'Por tempo'),
        ('hands', 'Por número de mãos'),
    ]
    blind_strategy = models.CharField(
        max_length=10,
        choices=BLIND_STRATEGY_CHOICES,
        default='fixed'
    )

    blind_interval = models.PositiveIntegerField(
        default=600,  # 10 minutos ou 10 mãos, depende da estratégia
        help_text="Intervalo para aumentar as blinds (segundos ou número de mãos)"
    )
    
    hands_played = models.PositiveIntegerField(default=0)

    STATUS_CHOICES = [
        ('waiting', 'Aguardando jogadores'),
        ('active', 'Em andamento'),
        ('closed', 'Finalizada'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='waiting'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'table'

    def __str__(self):
        return f"{self.name} ({self.status})"
    
class TablePlayer(models.Model):
    table = models.ForeignKey('Table', on_delete=models.CASCADE)
    player = models.ForeignKey('Player', on_delete=models.CASCADE)

    seat_number = models.PositiveIntegerField()
    chips = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)    # Ainda na mesa
    is_in_hand = models.BooleanField(default=True)   # Participando da mão atual
    is_all_in = models.BooleanField(default=False)
    is_eliminated = models.BooleanField(default=False)

    POSITION_CHOICES = [
        ('sb', 'Small Blind'),
        ('bb', 'Big Blind'),
        ('utg', 'Under the Gun'),
        ('utg+1', 'UTG+1'),
        ('utg+2', 'UTG+2'),
        ('lj', 'Lowjack'),
        ('hj', 'Hijack'),
        ('co', 'Cutoff'),
        ('btn', 'Button'),
        ('-', 'Indefinida'),
    ]
    position = models.CharField(
        max_length=10,
        choices=POSITION_CHOICES,
        default='-'
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'table_player'
        unique_together = ('table', 'player')

    def __str__(self):
        return f"{self.player.name} @ {self.table.name} (Seat {self.seat_number})"
    
class GameLog(models.Model):
    table = models.ForeignKey('Table', on_delete=models.CASCADE, related_name='logs')
    player = models.ForeignKey('Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')

    LOG_TYPE_CHOICES = [
        # Fluxo do jogo
        ('join', 'Entrada na mesa'),
        ('leave', 'Saída da mesa'),
        ('start', 'Início da partida'),
        ('position', 'Distribuição de posições'),

        # Ações do jogador
        ('fold', 'Desistiu (Fold)'),
        ('check', 'Passou (Check)'),
        ('call', 'Pagou (Call)'),
        ('bet', 'Apostou (Bet)'),
        ('raise', 'Aumentou (Raise)'),
        ('allin', 'All-in'),

        # Eventos técnicos ou de controle
        ('win', 'Vitória'),
        ('showdown', 'Showdown'),
        ('info', 'Informação'),
        ('error', 'Erro de execução'),
    ]
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES)
    
    ROUND_STAGE_CHOICES = [
        ('preflop', 'Pré-flop'),
        ('flop', 'Flop'),
        ('turn', 'Turn'),
        ('river', 'River'),
        ('showdown', 'Showdown'),
        ('-', 'Não aplicável'),
    ]
    round_stage = models.CharField(max_length=10, choices=ROUND_STAGE_CHOICES, default='-')
    
    hands_played = models.PositiveIntegerField(default=0)
    
    message = models.TextField()
    json_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'game_log'
        ordering = ['-created_at']  # logs mais recentes primeiro

    def __str__(self):
        jogador = self.player.name if self.player else 'Sistema'
        return f"[{self.created_at.strftime('%d/%m %H:%M')}] {self.log_type.upper()} - {jogador}: {self.message}"    