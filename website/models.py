from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator

class Wizard(models.Model):
    id = models.BigIntegerField(primary_key=True, unique=True) # wizard_id, USED ONLY FOR KNOWING IF DATA SHOULD BE UPDATED
    mana = models.BigIntegerField() # wizard_mana
    crystals = models.IntegerField() # wizard_crystal
    crystals_paid = models.IntegerField() # wizard_crystal_paid - need some analysis, because it can be a total-time or actual value, need more JSON files before doing something with its data
    last_login = models.DateTimeField() # wizard_last_login
    country = models.CharField(max_length=5) # wizard_last_country
    lang = models.CharField(max_length=5) # wizard_last_lang
    level = models.SmallIntegerField() # wizard_level
    energy = models.IntegerField() # wizard_energy
    energy_max = models.SmallIntegerField() # energy_max
    arena_wing = models.IntegerField() # arena_energy
    glory_point = models.IntegerField() # honor_point
    guild_point = models.IntegerField() # guild_point
    rta_point = models.IntegerField() # honor_medal
    rta_mark = models.IntegerField() # honor_mark - don't know what it is, for now 
    event_coin = models.IntegerField() # event_coint - Ancient Coins
    antibot_count = models.IntegerField() # quiz_reward_info.reward_count
    raid_level = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)]) # raid_info_list.available_stage_id
    storage_capacity = models.SmallIntegerField() # unit_depository_slots.number

    def __str__(self):
        return str(self.id)

class RuneSet(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=30)
    amount = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# Create your models here.
class Rune(models.Model):
    RUNE_QUALITIES = (
        (1, 'Common'),
        (2, 'Magic'),
        (3, 'Rare'),
        (4, 'Hero'),
        (5, 'Legend'),
        (11, 'Ancient Common'),
        (12, 'Ancient Magic'),
        (13, 'Ancient Rare'),
        (14, 'Ancient Hero'),
        (15, 'Ancient Legend'),
    )

    RUNE_EFFECTS = (
        (1, 'HP+'),
        (2, 'HP%'),
        (3, 'ATK+'),
        (4, 'ATK%'),
        (5, 'DEF+'),
        (6, 'DEF%'),
        (8, 'SPD'),
        (9, 'CRate%'),
        (10, 'CDmg%'),
        (11, 'RES%'),
        (12, 'ACC%'),
    )

    id = models.BigIntegerField(primary_key=True, unique=True) # rune_id
    user_id = models.ForeignKey(Wizard, on_delete=models.CASCADE) # wizard_id
    slot = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)]) # slot_no
    quality = models.SmallIntegerField(choices=RUNE_QUALITIES) # rank
    stars = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)]) # class
    rune_set = models.ForeignKey(RuneSet, on_delete=models.PROTECT) # set
    upgrade_limit = 15 # upgrade_limit
    upgrade_curr = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(upgrade_limit)]) #upgrade_curr
    base_value = models.IntegerField() # base_value
    sell_value = models.IntegerField() # sell_value
    primary = models.SmallIntegerField(choices=RUNE_EFFECTS) # pri_eff[0]
    primary_value = models.IntegerField() # pri_eff[1]
    innate = models.SmallIntegerField(choices=RUNE_EFFECTS) # prefix_eff[0]
    innate_value = models.IntegerField() # prefix_eff[1]
    substats = ArrayField( models.SmallIntegerField(choices=RUNE_EFFECTS) ) # sec_eff[i][0]
    substats_values = ArrayField( models.IntegerField() ) # sec_eff[i][1]
    substats_enchants = ArrayField( models.IntegerField() ) # sec_eff[i][2]
    substats_grindstones = ArrayField( models.IntegerField() ) # sec_eff[i][3]
    quality_original = models.SmallIntegerField(choices=RUNE_QUALITIES) # extra
    efficiency = models.FloatField(validators=[MinValueValidator(0.00)]) # to calculate in views
    efficiency_max = models.FloatField(validators=[MinValueValidator(0.00)]) # to calculate in views
    equipped = models.BooleanField() # occupied_type ( 1 - on monster, 2 - inventory, 0 - ? )
    # ^ OR same as JSON (,type if type different than monster then id = 0)
    # ^ OR models.BigIntegerField 
    # ^ OR models.ForeignKey for Monster [what with Inventory then?]
    # ^ OR occupied as a Boolean variable and then Foreign Key with possibility of being NULL
    # ^ OR occupied as a Boolean variable and then Monster has its key in class, there is only info if occupied [then needs to make a Trigger]

    def get_substats_display(self):
        effects = dict(self.RUNE_EFFECTS)
        strings = list()
        for substat in self.substats:
            if substat != 0:
                strings.append(effects[substat])
            else: 
                strings.append('-')
        return strings

    def get_substat_display(self, substat):
        effects = dict(self.RUNE_EFFECTS)
        return effects[substat]

    def __str__(self):
        return str(self.get_quality_display()) + ' ' + str(self.rune_set) + ' ' + str(self.get_primary_display()) + str(self.primary_value) + ' (slot: ' + str(self.slot) + ', eff: ' + str(self.efficiency) + ')'

    class Meta:
        ordering = ['slot', 'rune_set', '-efficiency', '-stars']

class MonsterFamily(models.Model):
    id = models.IntegerField(primary_key=True, unique=True) # unit_master_id, first 3 characters
    name = models.CharField(max_length=30) # mapping

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class MonsterBase(models.Model):
    MONSTER_ATTRIBUTES = [
        (1, 'Water'),
        (2, 'Fire'),
        (3, 'Wind'),
        (4, 'Light'),
        (5, 'Dark'),
    ]

    MONSTER_TYPES = [
        (0, 'None'),
        (1, 'Attack'),
        (2, 'Defense'),
        (3, 'HP'),
        (4, 'Support'),
        (5, 'Material'),
    ]

    MONSTER_AWAKEN = [
        (0, 'Unawakened'),
        (1, 'Awakened'),
        (2, '2A'),
    ]

    id = models.IntegerField(primary_key=True, unique=True) # unit_master_id
    family_id = models.ForeignKey(MonsterFamily, on_delete=models.PROTECT)
    base_class = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)]) # mapping
    name = models.CharField(max_length=50) # mapping
    attribute = models.SmallIntegerField(choices=MONSTER_ATTRIBUTES) # attribute
    archetype = models.SmallIntegerField(choices=MONSTER_TYPES) # last char from unit_master_id
    max_skills = ArrayField( models.IntegerField() ) # table with max skillsups ( we don't care about skills itself, it's in SWARFARM already )
    awaken = models.SmallIntegerField(choices=MONSTER_AWAKEN) # to calculate
    recommendation_text = models.CharField(max_length=512, blank=True, null=True) # best from Recommendation command, needs to delete every scam
    recommendation_votes = models.IntegerField(blank=True, null=True) # best from Recommendation command
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class MonsterHoh(models.Model):
    monster_id = models.ForeignKey(MonsterBase, on_delete=models.PROTECT)
    date_open = models.DateField()
    date_close = models.DateField()

    def __str__(self):
        return str(self.monster_id) + ' ( ' + self.date_open.strftime('%Y-%m-%d') + ' to ' + self.date_close.strftime('%Y-%m-%d') + ' )'

    class Meta:
        ordering = ['date_open', 'monster_id']

class MonsterFusion(models.Model):
    monster_id = models.ForeignKey(MonsterBase, on_delete=models.PROTECT)
    cost = models.IntegerField()

    def __str__(self):
        return str(self.monster_id)

    class Meta:
        ordering = ['monster_id']

class MonsterSource(models.Model):
    id = models.IntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=30)
    farmable = models.BooleanField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Monster(models.Model):
    id = models.BigIntegerField(primary_key=True, unique=True) # unit_id
    user_id = models.ForeignKey(Wizard, on_delete=models.CASCADE) # wizard_id
    base_monster = models.ForeignKey(MonsterBase, on_delete=models.PROTECT) # unit_master_id
    level = models.SmallIntegerField() # unit_level
    stars = models.SmallIntegerField() # class

    ############################################
    # all calculated during data upload, since we don't care about base values
    hp = models.IntegerField() # con - CON x 15 means base HP
    attack = models.IntegerField() # atk
    defense = models.IntegerField() # def
    speed = models.IntegerField() # spd
    res = models.IntegerField() # resist
    acc = models.IntegerField() # accuracy
    crit_rate = models.IntegerField() # critical_rate
    crit_dmg = models.IntegerField() # critical_damage
    avg_eff = models.FloatField(validators=[MinValueValidator(0.00)]) # sum(rune_eff) / len(runes)
    ############################################

    skills = ArrayField( models.IntegerField() ) # skills[i][1] - only skill levels, we don't care about skills itself, it's in SWARFARM already
    runes = models.ManyToManyField(Rune, related_name='equipped_runes', related_query_name='equipped_runes', blank=True) # runes
    created = models.DateTimeField() # create_time
    source = models.ForeignKey(MonsterSource, on_delete=models.PROTECT) # source
    transmog = models.BooleanField() # costume_master_id
    locked = models.BooleanField() # unit_lock_list - if it's in the array
    storage = models.BooleanField() # building_id, need to check which one is storage building
    

    def __str__(self):
        return str(self.base_monster) + ' ( ID: ' + str(self.id) + ' )'

    class Meta:
        ordering = ['-stars', '-level', 'base_monster']

class MonsterRep(models.Model):
    wizard_id = models.ForeignKey(Wizard, on_delete=models.CASCADE) # wizard_info
    monster_id = models.ForeignKey(Monster, on_delete=models.CASCADE) # rep_unit_id in profile JSON - wizard_info part

class Deck(models.Model):
    DECK_TYPES = [
        (1, 'Arena'),
        (2, 'Guild War'),
        (3, 'Raid'),
        (4, 'Lab Normal'),
        (5, 'Lab Rescue'),
        (6, 'ToA'),
        (7, 'Lab Speed Limit'),
        (8, 'Lab Time Limit'),
        (9, 'Lab Cooldown'),
        (10, 'Lab Explode'),
        (11, 'Lab Boss'),
    ]

    id = models.BigAutoField(primary_key=True, unique=True)
    wizard_id = models.ForeignKey(Wizard, on_delete=models.CASCADE)
    place = models.IntegerField(choices=DECK_TYPES) # deck_list.deck_type
    number = models.SmallIntegerField() # deck_list.deck_seq
    monsters = models.ManyToManyField(Monster, related_name='monsters_in_deck', related_query_name='monsters_in_deck') # deck_list.unit_id_list
    leader = models.ForeignKey(Monster, on_delete=models.CASCADE) # deck_list.leader_unit_id

    class Meta:
        ordering = ['wizard_id', 'place', 'number']

class Building(models.Model):
    AREA_TYPE = (
        (0, 'Arena'),
        (1, 'Guild'),
    )

    id = models.IntegerField(primary_key=True, unique=True)
    area = models.IntegerField(choices=AREA_TYPE)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name + ' [ ' + str(self.get_area_display()) + ' ]'

    class Meta:
        ordering = ['area', 'name']

class WizardBuilding(models.Model):
    wizard_id = models.ForeignKey(Wizard, on_delete=models.CASCADE)
    building_id = models.ForeignKey(Building, on_delete=models.CASCADE)
    level = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], default=0)

    def __str__(self):
        return str(self.wizard_id) + ' ' + str(self.building_id) + ' ( level ' + str(self.level) + ' )'

    class Meta:
        ordering = ['wizard_id', '-level', 'building_id']


class Arena(models.Model):
    RANKS = (
        (901, 'Beginner'),

        (1001, 'Challenger I'),
        (1002, 'Challenger II'),
        (1003, 'Challenger III'),

        (2001, 'Fighter I'),
        (2002, 'Fighter II'),
        (2003, 'Fighter III'),

        (3001, 'Conqueror I'),
        (3002, 'Conqueror II'),
        (3003, 'Conqueror III'),

        (4001, 'Guardian I'),
        (4002, 'Guardian II'),
        (4003, 'Guardian III'),

        (5001, 'Legend'),
    )

    wizard_id = models.ForeignKey(Wizard, on_delete=models.CASCADE) # wizard_id
    wins = models.IntegerField() # arena_win
    loses = models.IntegerField() # arena_lose
    rank = models.IntegerField(choices=RANKS) # rating_id
    def_1 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="first_def_monster", null=True, default=None) # defense_unit_list: unit_id & pos_id
    def_2 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="second_def_monster", null=True, default=None)
    def_3 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="third_def_monster", null=True, default=None)
    def_4 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="fourth_def_monster", null=True, default=None)

    def __str__(self):
        return str(self.wizard_id) + ': ' + str(self.get_rank_display()) + ' ( W' + str(self.wins) + '/' + str(self.loses) + 'L )'

    class Meta:
        ordering = ['-rank', '-wins', 'loses']