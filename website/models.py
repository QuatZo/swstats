from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.
class Command(models.Model):
    COMMAND_TYPES = (
        (1, 'Request'),
        (2, 'Response'),
        (3, 'Both'),
    )

    name = models.CharField(max_length=128)
    message_type = models.IntegerField(choices=COMMAND_TYPES)

class Guild(models.Model):
    GUILD_RANKS = (
        (1011, 'Challenger'),

        (2011, 'Fighter I'),
        (2012, 'Fighter II'),
        (2013, 'Fighter III'),

        (3011, 'Conqueror I'),
        (3012, 'Conqueror II'),
        (3013, 'Conqueror III'),

        (4011, 'Guardian I'),
        (4012, 'Guardian II'),
        (4013, 'Guardian III'),

        (5011, 'Legend'),
    )

    SIEGE_RANKS = (
        (1001, 'Challenger'),

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

    id = models.IntegerField(primary_key=True, unique=True) # guild.guild_info.guild_id
    level = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(30)]) # guild.guild_info.level
    members_max = 30
    members_amount = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(members_max)]) # guild.guild_info.member_now
    gw_best_place = models.IntegerField() # guildwar_ranking_stat.best.rank
    gw_best_ranking = models.IntegerField(choices=GUILD_RANKS) # guildwar_ranking_stat.best.rating_id
    siege_ranking = models.IntegerField(choices=SIEGE_RANKS, null=True, blank=True)
    last_update = models.DateTimeField()

    def __str__(self):
        return str(self.id) + ' (' + str(self.members_amount) + '/' + str(self.members_max) + ', ' + str(self.gw_best_ranking) + ' [Rank: ' + str(self.gw_best_place) + '])'

    class Meta:
        ordering = ['-gw_best_place', '-gw_best_ranking', '-level', '-members_amount', 'id']

    @classmethod
    def get_siege_ranking_name(cls, ranking_id):
        if ranking_id is None or not ranking_id:
            return "Unknown"
        return dict(cls.SIEGE_RANKS)[ranking_id]

    @classmethod
    def get_guild_ranking_names(cls):
        return dict(cls.GUILD_RANKS)

    @classmethod
    def get_guild_ranking_name(cls, ranking_id):
        if ranking_id is None or not ranking_id:
            return "Unknown"
        return dict(cls.GUILD_RANKS)[ranking_id]

class Wizard(models.Model):
    id = models.BigIntegerField(primary_key=True, unique=True, db_index=True) # wizard_id, USED ONLY FOR KNOWING IF DATA SHOULD BE UPDATED
    mana = models.BigIntegerField(blank=True, null=True, default=None) # wizard_mana
    crystals = models.IntegerField(blank=True, null=True, default=None) # wizard_crystal
    crystals_paid = models.IntegerField(blank=True, null=True, default=None) # wizard_crystal_paid - need some analysis, because it can be a total-time or actual value, need more JSON files before doing something with its data
    last_login = models.DateTimeField(blank=True, null=True, default=None) # wizard_last_login
    country = models.CharField(max_length=5, blank=True, null=True, default=None) # wizard_last_country
    lang = models.CharField(max_length=5, blank=True, null=True, default=None) # wizard_last_lang
    level = models.SmallIntegerField(blank=True, null=True, default=None) # wizard_level
    energy = models.IntegerField(blank=True, null=True, default=None) # wizard_energy
    energy_max = models.SmallIntegerField(blank=True, null=True, default=None) # energy_max
    arena_wing = models.IntegerField(blank=True, null=True, default=None) # arena_energy
    glory_point = models.IntegerField(blank=True, null=True, default=None) # honor_point
    guild_point = models.IntegerField(blank=True, null=True, default=None) # guild_point
    rta_point = models.IntegerField(blank=True, null=True, default=None) # honor_medal
    rta_mark = models.IntegerField(blank=True, null=True, default=None) # honor_mark - don't know what it is, for now 
    event_coin = models.IntegerField(blank=True, null=True, default=None) # event_coint - Ancient Coins
    antibot_count = models.IntegerField(blank=True, null=True, default=None) # quiz_reward_info.reward_count
    raid_level = models.SmallIntegerField(blank=True, null=True, default=None, validators=[MinValueValidator(1), MaxValueValidator(5)]) # raid_info_list.available_stage_id
    storage_capacity = models.SmallIntegerField(blank=True, null=True, default=None) # unit_depository_slots.number
    guild = models.ForeignKey(Guild, blank=True, null=True, on_delete=models.SET_NULL, db_index=True)
    last_update = models.DateTimeField()

    def __str__(self):
        return str(self.id)

class RuneSet(models.Model):
    id = models.IntegerField(primary_key=True, unique=True, db_index=True)
    name = models.CharField(max_length=30, db_index=True)
    amount = models.IntegerField(db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Rune(models.Model):
    RUNE_QUALITIES = (
        (0, 'Unknown'), # old runes before 'extra' addition for every rune in JSON file
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

    id = models.BigIntegerField(primary_key=True, unique=True, db_index=True) # rune_id
    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE, db_index=True) # wizard_id
    slot = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)], db_index=True) # slot_no
    quality = models.SmallIntegerField(choices=RUNE_QUALITIES, db_index=True) # rank
    stars = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)], db_index=True) # class
    rune_set = models.ForeignKey(RuneSet, on_delete=models.PROTECT, db_index=True) # set
    upgrade_limit = 15 # upgrade_limit
    upgrade_curr = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(upgrade_limit)], db_index=True) #upgrade_curr
    base_value = models.IntegerField() # base_value
    sell_value = models.IntegerField() # sell_value
    primary = models.SmallIntegerField(choices=RUNE_EFFECTS, db_index=True) # pri_eff[0]
    primary_value = models.IntegerField(db_index=True) # pri_eff[1]
    innate = models.SmallIntegerField(choices=RUNE_EFFECTS, blank=True, null=True, db_index=True) # prefix_eff[0]
    innate_value = models.IntegerField(blank=True, null=True, db_index=True) # prefix_eff[1]
    
    ########################################
    # Substats
    sub_hp_flat = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_hp = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_atk_flat = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_atk = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_def_flat = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_def = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_speed = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_crit_rate = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_crit_dmg = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_res = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    sub_acc = ArrayField(models.SmallIntegerField(), blank=True, null=True, db_index=True)
    ########################################

    quality_original = models.SmallIntegerField(choices=RUNE_QUALITIES, db_index=True) # extra
    efficiency = models.FloatField(validators=[MinValueValidator(0.00)], db_index=True) # to calculate in views
    efficiency_max = models.FloatField(validators=[MinValueValidator(0.00)], db_index=True) # to calculate in views
    equipped = models.BooleanField(db_index=True) # occupied_type ( 1 - on monster, 2 - inventory, 0 - ? )
    locked = models.BooleanField(db_index=True) # rune_lock_list

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

    @classmethod
    def get_rune_quality(cls, number):
        return dict(cls.RUNE_QUALITIES)[number]

    @classmethod
    def get_rune_quality_id(cls, name):
        for key, quality in dict(cls.RUNE_QUALITIES).items():
            if quality == name:
                return key

    @classmethod
    def get_rune_primary(cls, number):
        return dict(cls.RUNE_EFFECTS)[number]

    @classmethod
    def get_rune_primary_id(cls, name):
        for key, primary in dict(cls.RUNE_EFFECTS).items():
            stat = name.replace('plus', '+').replace('percent', '%')
            if primary == stat:
                return key

class MonsterFamily(models.Model):
    id = models.IntegerField(primary_key=True, unique=True, db_index=True) # unit_master_id, first 3 characters
    name = models.CharField(max_length=30, db_index=True) # mapping

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

    id = models.IntegerField(primary_key=True, unique=True, db_index=True) # unit_master_id
    family = models.ForeignKey(MonsterFamily, on_delete=models.PROTECT, db_index=True)
    base_class = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)], db_index=True) # mapping
    name = models.CharField(max_length=50, db_index=True) # mapping
    attribute = models.SmallIntegerField(choices=MONSTER_ATTRIBUTES) # attribute
    archetype = models.SmallIntegerField(choices=MONSTER_TYPES) # last char from unit_master_id
    max_skills = ArrayField( models.IntegerField(db_index=True) ) # table with max skillsups ( we don't care about skills itself, it's in SWARFARM already )
    awaken = models.SmallIntegerField(choices=MONSTER_AWAKEN, db_index=True) # to calculate
    recommendation_text = models.CharField(max_length=512, blank=True, null=True) # best from Recommendation command, needs to delete every scam
    recommendation_votes = models.IntegerField(blank=True, default=0) # best from Recommendation command
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

    @classmethod
    def get_attributes_as_dict(cls):
        return dict(cls.MONSTER_ATTRIBUTES)
    
    @classmethod
    def get_types_as_dict(cls):
        return dict(cls.MONSTER_TYPES)
    
    @classmethod
    def get_awaken_as_dict(cls):
        return dict(cls.MONSTER_AWAKEN)

    @classmethod
    def get_attribute_id(cls, name):
        for key, attribute in dict(cls.MONSTER_ATTRIBUTES).items():
            if attribute == name:
                return key

    @classmethod
    def get_archetype_id(cls, name):
        for key, archetype in dict(cls.MONSTER_TYPES).items():
            if archetype == name:
                return key

class MonsterHoh(models.Model):
    monster = models.ForeignKey(MonsterBase, on_delete=models.PROTECT, db_index=True)
    date_open = models.DateField()
    date_close = models.DateField()

    def __str__(self):
        return str(self.monster) + ' (' + self.date_open.strftime('%Y-%m-%d') + ' to ' + self.date_close.strftime('%Y-%m-%d') + ')'

    class Meta:
        ordering = ['date_open', 'monster']

class MonsterFusion(models.Model):
    monster = models.ForeignKey(MonsterBase, on_delete=models.PROTECT, db_index=True)
    cost = models.IntegerField()

    def __str__(self):
        return str(self.monster)

    class Meta:
        ordering = ['monster']

class MonsterSource(models.Model):
    id = models.IntegerField(primary_key=True, unique=True, db_index=True)
    name = models.CharField(max_length=30)
    farmable = models.BooleanField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Monster(models.Model):
    id = models.BigIntegerField(primary_key=True, unique=True, db_index=True) # unit_id
    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE, db_index=True) # wizard_id
    base_monster = models.ForeignKey(MonsterBase, on_delete=models.PROTECT, db_index=True) # unit_master_id
    level = models.SmallIntegerField(db_index=True) # unit_level
    stars = models.SmallIntegerField(db_index=True) # class

    ############################################
    # all calculated during data upload, since we don't care about base values
    hp = models.IntegerField(db_index=True) # con - CON x 15 means base HP
    attack = models.IntegerField(db_index=True) # atk
    defense = models.IntegerField(db_index=True) # def
    speed = models.IntegerField(db_index=True) # spd
    res = models.IntegerField(db_index=True) # resist
    acc = models.IntegerField(db_index=True) # accuracy
    crit_rate = models.IntegerField(db_index=True) # critical_rate
    crit_dmg = models.IntegerField(db_index=True) # critical_damage
    avg_eff = models.FloatField(validators=[MinValueValidator(0.00)], db_index=True) # sum(rune_eff) / len(runes)
    eff_hp = models.IntegerField(validators=[MinValueValidator(0.00)], db_index=True)
    eff_hp_def_break = models.IntegerField(validators=[MinValueValidator(0.00)], db_index=True)
    ############################################

    skills = ArrayField( models.IntegerField(db_index=True) ) # skills[i][1] - only skill levels, we don't care about skills itself, it's in SWARFARM already
    runes = models.ManyToManyField(Rune, related_name='equipped_runes', related_query_name='equipped_runes', blank=True, db_index=True) # runes
    created = models.DateTimeField(db_index=True) # create_time
    source = models.ForeignKey(MonsterSource, on_delete=models.PROTECT) # source
    transmog = models.BooleanField() # costume_master_id
    locked = models.BooleanField() # unit_lock_list - if it's in the array
    storage = models.BooleanField() # building_id, need to check which one is storage building

    def __str__(self):
        return str(self.base_monster) + ' (ID: ' + str(self.id) + ')'

    class Meta:
        ordering = ['-stars', '-level', 'base_monster']

class MonsterRep(models.Model):
    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE, db_index=True) # wizard_info
    monster = models.ForeignKey(Monster, on_delete=models.CASCADE, db_index=True) # rep_unit_id in profile JSON - wizard_info part

class RuneRTA(models.Model):
    monster = models.ForeignKey(Monster, on_delete=models.CASCADE, db_index=True)
    rune = models.ForeignKey(Rune, on_delete=models.CASCADE, db_index=True)

    def __str__(self):
        return str(self.rune) + " on " + str(self.monster)

    class Meta:
        verbose_name = 'Rune RTA'
        verbose_name_plural = 'Runes RTA'
        ordering = ['monster', 'rune']

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

    id = models.BigAutoField(primary_key=True, unique=True, db_index=True)
    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE, db_index=True)
    place = models.IntegerField(choices=DECK_TYPES, db_index=True) # deck_list.deck_type
    number = models.SmallIntegerField() # deck_list.deck_seq
    monsters = models.ManyToManyField(Monster, related_name='monsters_in_deck', related_query_name='monsters_in_deck', db_index=True) # deck_list.unit_id_list
    leader = models.ForeignKey(Monster, on_delete=models.CASCADE, db_index=True) # deck_list.leader_unit_id
    team_runes_eff = models.FloatField(validators=[MinValueValidator(0.00)], db_index=True) # to calculate, by using monster's avg_eff

    def __str__(self):
        return "Deck for " +  dict(self.DECK_TYPES)[self.place]

    class Meta:
        ordering = ['-team_runes_eff', 'place', 'number']

    @classmethod
    def get_place_id(cls, name):
        for key, place in dict(cls.DECK_TYPES).items():
            if place == name:
                return key

class Building(models.Model):
    AREA_TYPE = (
        (0, 'Arena'),
        (1, 'Guild'),
    )

    id = models.IntegerField(primary_key=True, unique=True, db_index=True)
    area = models.IntegerField(choices=AREA_TYPE)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name + ' [ ' + str(self.get_area_display()) + ' ]'

    class Meta:
        ordering = ['area', 'name']

class WizardBuilding(models.Model):
    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE, db_index=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, db_index=True)
    level = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], default=0, db_index=True)

    def __str__(self):
        return str(self.wizard) + ' ' + str(self.building) + ' (level ' + str(self.level) + ')'

    class Meta:
        ordering = ['wizard', '-level', 'building']

class Arena(models.Model):
    ARENA_RANKS = (
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

    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE, db_index=True) # wizard_id
    wins = models.IntegerField() # arena_win
    loses = models.IntegerField() # arena_lose
    rank = models.IntegerField(choices=ARENA_RANKS, db_index=True) # rating_id
    def_1 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="first_def_monster", null=True, default=None, db_index=True) # defense_unit_list: unit_id & pos_id
    def_2 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="second_def_monster", null=True, default=None, db_index=True)
    def_3 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="third_def_monster", null=True, default=None, db_index=True)
    def_4 = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="fourth_def_monster", null=True, default=None, db_index=True)

    def __str__(self):
        return str(self.wizard) + ': ' + str(self.get_rank_display()) + ' (W' + str(self.wins) + '/' + str(self.loses) + 'L)'

    class Meta:
        ordering = ['-rank', '-wins', 'loses']

class HomunculusSkill(models.Model):
    id = models.IntegerField(primary_key=True, unique=True, db_index=True) # id
    name = models.CharField(max_length=50, db_index=True)  # name
    description = models.CharField(max_length=512, db_index=True) # description
    depth = models.SmallIntegerField(db_index=True) # depth
    letter = models.CharField(max_length=1, null=True, db_index=True) # letter

    def __str__(self):
        return self.name + ' [Path: ' + self.letter + ']'  + ' [Depth: ' + str(self.depth) + ']'

    class Meta:
        ordering = ['depth', 'id']

class HomunculusBuild(models.Model):
    homunculus = models.ForeignKey(MonsterBase, on_delete=models.CASCADE, db_index=True)
    depth_1 = models.ForeignKey(HomunculusSkill, on_delete=models.CASCADE, related_name="depth_1", null=True, default=None, db_index=True)
    depth_2 = models.ForeignKey(HomunculusSkill, on_delete=models.CASCADE, related_name="depth_2", null=True, default=None, db_index=True)
    depth_3 = models.ForeignKey(HomunculusSkill, on_delete=models.CASCADE, related_name="depth_3", null=True, default=None, db_index=True)
    depth_4 = models.ForeignKey(HomunculusSkill, on_delete=models.CASCADE, related_name="depth_4", null=True, default=None, db_index=True)
    depth_5 = models.ForeignKey(HomunculusSkill, on_delete=models.CASCADE, related_name="depth_5", null=True, default=None, db_index=True)

    def __str__(self):
        return '-'.join([ self.depth_1.letter, self.depth_2.letter, self.depth_3.letter, self.depth_4.letter, self.depth_5.letter ])

    def get_build_str(self):
        return __str__(self)
    
    class Meta:
        ordering = [ 'id' ]

class WizardHomunculus(models.Model):
    homunculus = models.ForeignKey(Monster, on_delete=models.CASCADE, db_index=True) # homunculus_skill_list[el].unit_id
    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE, db_index=True) # homunculus_skill_list[el].unit_id
    build = models.ForeignKey(HomunculusBuild, on_delete=models.CASCADE, null=True, db_index=True) 

    @classmethod
    def get_build_display(cls, id):
        return str(HomunculusBuild.objects.get(id=id))

    def __str__(self):
        return str(self.homunculus) + '(' + str(self.build) + ')'

    class Meta:
        ordering = ['wizard', 'homunculus']

class Item(models.Model):
    ITEM_TYPES = (
        (6, "?"),
        (9, "Scroll"),
        (11, "Essence"),
        (12, "Monster Pieces"),
        (15, "??"),
        (16, "???"),
        (19, "????"),
        (20, "????????"),
        (29, "Crafting Material"),
        (37, "?????"),
        (57, "??????"),
        (58, "???????"),
        (61, "Evolve Material"),
    )

    item_id = models.IntegerField()
    item_type = models.SmallIntegerField(choices=ITEM_TYPES)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['item_type', 'item_id']

class WizardItem(models.Model):
    wizard = models.ForeignKey(Wizard, on_delete=models.CASCADE)
    master_item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return 'x' + str(self.quantity) + ' ' + str(self.master_item)

    class Meta:
        ordering = ['wizard', 'master_item', '-quantity']

class DungeonRun(models.Model):
    """Uses 'BattleDungeonResult' command"""
    DUNGEON_TYPES = (
        (1001, 'Hall of Dark'),
        (2001, 'Hall of Fire'),
        (3001, 'Hall of Water'),
        (4001, 'Hall of Wind'),
        (5001, 'Hall of Magic'),
        (6001, 'Necropolis'),
        (7001, 'Hall of Light'),
        (8001, 'Giants Keep'),
        (9001, 'Dragons Lair'),
        (999999999, 'Rift of Worlds'), # couldn't find Dungeon ID for this, since it's not exactly a dungeon
    )

    id = models.BigAutoField(primary_key=True, unique=True, db_index=True)
    wizard = models.ForeignKey(Wizard, null=True, on_delete=models.SET_NULL, db_index=True, blank=True) # wizard_id, response; if not exists then wizard_info in request
    dungeon = models.IntegerField(choices=DUNGEON_TYPES, db_index=True) # dungeon_id, request
    stage = models.IntegerField() # stage_id, request
    win = models.BooleanField() # win_lose, request & response
    clear_time = models.DurationField(null=True, blank=True, db_index=True) # clear_time, current_time -> i.e. 85033 -> 1:25,033 (min:sec,milisec)
    monsters = models.ManyToManyField(Monster, db_index=True, related_name='dungeon_monsters') # unit_list, response
    date = models.DateTimeField(db_index=True) # tvalue

    def __str__(self):
        return self.get_dungeon_display() + ' B' + str(self.stage) + ' (' + str(self.clear_time) + ')'
    
    class Meta:
        ordering = ['dungeon', '-stage', '-clear_time', '-win']

    @classmethod
    def get_dungeon_name(cls, id):
        try:
            return dict(cls.DUNGEON_TYPES)[id]
        except KeyError:
            return None

    @classmethod
    def get_dungeon_id(cls, name):
        for key, dungeon in dict(cls.DUNGEON_TYPES).items():
            if dungeon == name:
                return key
        return None

    @classmethod
    def get_all_dungeons(cls):
        return dict(cls.DUNGEON_TYPES).values()
     
class RaidBattleKey(models.Model):
    battle_key = models.BigIntegerField(primary_key=True, unique=True) # battle_info.battle_key
    stage = models.IntegerField() # battle_info.room_info.stage_id

class RiftDungeonRun(models.Model):
    """Uses 'BattleRiftDungeonResult' and 'BattleRiftDungeonStart' command"""
    DUNGEON_TYPES = (
        (1001, 'Ice Beast'),
        (2001, 'Fire Beast'),
        (3001, 'Wind Beast'),
        (4001, 'Light Beast'),
        (5001, 'Dark Beast'),
    )
    CLEAR_RATINGS = (
        (1, 'F'),
        (2, 'D'),
        (3, 'C'),
        (4, 'B-'),
        (5, 'B'),
        (6, 'B+'),
        (7, 'A-'),
        (8, 'A'),
        (9, 'A+'),
        (10, 'S'),
        (11, 'SS'),
        (12, 'SSS'),
    )

    battle_key = models.BigIntegerField(primary_key=True, unique=True, db_index=True) # BattleRiftDungeonStart, response, battle_key
    wizard = models.ForeignKey(Wizard, null=True, on_delete=models.SET_NULL, db_index=True) # BattleRiftDungeonStart response, wizard_info, wizard_id; if not exists then wizard_info in request
    dungeon = models.IntegerField(choices=DUNGEON_TYPES, db_index=True) # BattleRiftDungeonStart,  request, dungeon_id
    win = models.BooleanField(null=True, blank=True) # BattleRiftDungeonResult, request, battle_result (1 - win, 2 - lost)
    clear_time = models.DurationField(null=True, blank=True, db_index=True) # BattleRiftDungeonResult, request, clear_time -> i.e. 85033 -> 1:25,033 (min:sec,milisec)
    clear_rating = models.IntegerField(choices=CLEAR_RATINGS, null=True, blank=True, db_index=True) # BattleRiftDungeonResult, response, rift_dungeon_box_id (or by calculating damage)
    dmg_phase_1 = models.IntegerField(default=0) # BattleRiftDungeonResult, request, round_list[0][1]
    dmg_phase_glory = models.IntegerField(default=0) # BattleRiftDungeonResult, request, round_list[1][1]
    dmg_phase_2 = models.IntegerField(default=0) # BattleRiftDungeonResult, request, round_list[2][1]
    dmg_total =  models.IntegerField(db_index=True) # overrided save function
    monsters = models.ManyToManyField(Monster, db_index=True, related_name='rift_dungeon_monsters') # BattleRiftDungeonStart, request, unit_id_list
    date = models.DateTimeField(null=True, blank=True, db_index=True) # BattleRiftDungeonStart, response, tvalue

    # override save function, to calculate total dmg automatically
    def save(self, *args, **kwargs):
        self.dmg_total = self.dmg_phase_1 + self.dmg_phase_glory + self.dmg_phase_2
        super().save(*args, **kwargs)

    def __str__(self):
            return self.get_dungeon_display() + ' B1 (' + str(self.clear_time) + ')'


    class Meta:
        ordering = ['dungeon', '-clear_rating', '-dmg_total']

    @classmethod
    def get_dungeon_name(cls, id):
        return dict(cls.DUNGEON_TYPES)[id]

    @classmethod
    def get_dungeon_id(cls, name):
        for key, dungeon in dict(cls.DUNGEON_TYPES).items():
            if dungeon == name:
                return key

    @classmethod
    def get_all_dungeons(cls):
        return dict(cls.DUNGEON_TYPES).values()

    @classmethod
    def get_rating_name(cls, id):
        return dict(cls.CLEAR_RATINGS)[id]

class SiegeRecord(models.Model):
    # id - response; defense_deck_list; deck_id
    wizard = models.ForeignKey(Wizard, on_delete=models.SET_NULL, db_index=True, null=True, blank=True) # response; wizard_info_list, wizard_id
    monsters = models.ManyToManyField(Monster, related_name="siege_defense_monsters", db_index=True) # response; defense_unit_list; unit_info; unit_id;
    leader = models.ForeignKey(Monster, on_delete=models.CASCADE, related_name="siege_defense_leader", null=True, blank=True, db_index=True) # response; defense_unit_list; pos_id = 1;
    win = models.IntegerField() # response; defense_deck_list; win_count
    lose = models.IntegerField() # response; defense_deck_list; lose_count
    ratio = models.FloatField(db_index=True) # response; defense_deck_list; winning_rate
    last_update = models.DateTimeField() # response; tvalue
    full = models.BooleanField(default=True) # override save method

    # override save method, to set if defense has 3 monsters
    def save(self, *args, **kwargs):
        if self.monsters.all().count() != 3:
            self.full = False
        else:
            self.full = True
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id) + ' (' + str(self.win) + '/' + str(self.lose) + ')'

    class Meta:
        ordering = ['-win', '-ratio']

class DimensionHoleRun(models.Model):
    DIM_HOLE_TYPES = (
        (1101, 'Ellunia'),
        (1201, 'Fairy (Ellunia)'),
        (1202, 'Pixie (Ellunia)'),

        (2101, 'Karzhan'),
        (2201, 'Warbear (Karzhan)'),
        (2202, 'Inugami (Karzhan)'),
        (2203, 'Griffon (Karzhan)'),

        (3101, 'Lumel'),
        (3201, 'Werewolf (Lumel)'),
        (3202, 'Martial Cat (Lumel)'),
    )

    # id - request; battle_key
    wizard = models.ForeignKey(Wizard, null=True, on_delete=models.SET_NULL, db_index=True) # wizard_info.wizard_id, response; if not exists then whole wizard_info in response
    dungeon = models.IntegerField(choices=DIM_HOLE_TYPES, db_index=True) # dungeon_id, request
    stage = models.IntegerField() # difficulty, response
    win = models.BooleanField() # win_lose, response
    practice = models.BooleanField() # practice_mode, response
    clear_time = models.DurationField(null=True, blank=True, db_index=True) # response; clear_time.current_time -> i.e. 85033 -> 1:25,033 (min:sec,milisec)
    monsters = models.ManyToManyField(Monster, db_index=True, related_name="dimhole_monsters", related_query_name="dimhole_monsters") # unit_id_list; request
    date = models.DateTimeField(db_index=True) # tvalue; response

    def __str__(self):
        return str(self.dungeon) + ' B' + str(self.stage) + ' [' + str(self.clear_time) + ']'

    class Meta:
        ordering = ['dungeon', '-stage', 'clear_time', 'win']

    @classmethod
    def get_dungeon_name(cls, identifier):
        return dict(cls.DIM_HOLE_TYPES)[identifier]

    @classmethod
    def get_dungeon_id_by_name(cls, name):
        for key, val in dict(cls.DIM_HOLE_TYPES).items():
            if val == name:
                return key