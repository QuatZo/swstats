from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator

class Wizard(models.Model):
    id = models.BigIntegerField(primary_key=True, unique=True) # wizard_id, USED ONLY FOR KNOWING IF DATA SHOULD BE UPDATED
    mana = models.IntegerField() # wizard_mana
    crystals = models.IntegerField() # wizard_crystal
    crystals_paid = models.IntegerField() # wizard_crystal_paid - need some analysis, because it can be a total-time or actual value, need more JSON files before doing something with its data
    last_login = models.DateTimeField() # wizard_last_login
    country = models.CharField(max_length=5) # wizard_last_country
    lang = models.CharField(max_length=5) # wizard_last_lang
    level = models.IntegerField() # wizard_level
    energy = models.IntegerField() # wizard_energy
    energy_max = models.IntegerField() # energy_max
    arena_wing = models.IntegerField() # arena_energy
    glory_point = models.IntegerField() # honor_point
    guild_point = models.IntegerField() # guild_point
    rta_point = models.IntegerField() # honor_medal
    rta_mark = models.IntegerField() # honor_mark - don't know what it is, for now 
    event_coin = models.IntegerField() # event_coint - Ancient Coins

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
        (1, 'HP +'),
        (2, 'HP %'),
        (3, 'ATK +'),
        (4, 'ATK %'),
        (5, 'DEF +'),
        (6, 'DEF %'),
        (8, 'SPD +'),
        (9, 'CRate %'),
        (10, 'CDmg %'),
        (11, 'RES %'),
        (12, 'ACC %'),
    )

    id = models.BigIntegerField(primary_key=True, unique=True) # rune_id
    user_id = models.ForeignKey(Wizard, on_delete=models.CASCADE) # wizard_id
    slot = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)]) # slot_no
    quality = models.IntegerField(choices=RUNE_QUALITIES) # rank
    stars = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)]) # class
    rune_set = models.ForeignKey(RuneSet, on_delete=models.PROTECT) # set
    upgrade_limit = 15 # upgrade_limit
    upgrade_curr = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(upgrade_limit)]) #upgrade_curr
    base_value = models.IntegerField() # base_value
    sell_value = models.IntegerField() # sell_value
    primary = models.IntegerField(choices=RUNE_EFFECTS) # pri_eff[0]
    primary_value = models.IntegerField() # pri_eff[1]
    innate = models.IntegerField(choices=RUNE_EFFECTS) # prefix_eff[0]
    innate_value = models.IntegerField() # prefix_eff[1]
    substats = ArrayField( models.IntegerField(choices=RUNE_EFFECTS) ) # sec_eff[i][0]
    substats_values = ArrayField( models.IntegerField() ) # sec_eff[i][1]
    substats_enchants = ArrayField( models.IntegerField() ) # sec_eff[i][2]
    substats_grindstones = ArrayField( models.IntegerField() ) # sec_eff[i][3]
    quality_original = models.IntegerField(choices=RUNE_QUALITIES) # extra
    efficiency = models.FloatField(validators=[MinValueValidator(0.00)]) # to calculate in views
    efficiency_max = models.FloatField(validators=[MinValueValidator(0.00)]) # to calculate in views
    equipped = models.BooleanField() # occupied_type ( 1 - on monster, 2 - inventory, 0 - ? )
    # ^ OR same as JSON (,type if type different than monster then id = 0)
    # ^ OR models.BigIntegerField 
    # ^ OR models.ForeignKey for Monster [what with Inventory then?]
    # ^ OR occupied as a Boolean variable and then Foreign Key with possibility of being NULL
    # ^ OR occupied as a Boolean variable and then Monster has its key in class, there is only info if occupied [then needs to make a Trigger]

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
    base_class = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)]) # mapping
    name = models.CharField(max_length=50) # mapping
    attribute = models.IntegerField(choices=MONSTER_ATTRIBUTES) # attribute
    archetype = models.IntegerField(choices=MONSTER_TYPES) # last char from unit_master_id
    max_skills = ArrayField( models.IntegerField() ) # table with max skillsups ( we don't care about skills itself, it's in SWARFARM already )
    awaken = models.IntegerField(choices=MONSTER_AWAKEN) # to calculate
    recommendation_text = models.CharField(max_length=512, blank=True, null=True) # best from Recommendation command, needs to delete every scam
    recommendation_votes = models.IntegerField(blank=True, null=True) # best from Recommendation command
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

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
    level = models.IntegerField() # unit_level
    stars = models.IntegerField() # class

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
    storage = models.BooleanField() # building_id, need to check which one is storage building
    source = models.ForeignKey(MonsterSource, on_delete=models.PROTECT) # source

    def __str__(self):
        return str(self.base_monster) + ' ( ID: ' + str(self.id) + ' )'

class MonsterRep(models.Model):
    wizard_id = models.ForeignKey(Wizard, on_delete=models.PROTECT) # wizard_info
    monster_id = models.ForeignKey(Monster, on_delete=models.PROTECT) # rep_unit_id in profile JSON - wizard_info part