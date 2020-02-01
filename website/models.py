from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator

class RuneSet(models.Model):
    name = models.CharField(max_length=30)
    amount = models.IntegerField()

# Create your models here.
class Rune(models.Model):
    RUNE_QUALITIES = [
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
    ]

    RUNE_EFFECTS = [
        (1, 'HP flat'),
        (2, 'HP%'),
        (3, 'ATK flat'),
        (4, 'ATK%'),
        (5, 'DEF flat'),
        (6, 'DEF%'),
        (8, 'SPD'),
        (9, 'CRate'),
        (10, 'CDmg'),
        (11, 'RES'),
        (12, 'ACC'),
    ]

    id = models.BigIntegerField(primary_key=True, unique=True) # rune_id
    slot = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(6)]) # slot_no
    quality = models.IntegerField(choices=RUNE_QUALITIES) # rank
    stars = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(6)]) # class
    rune_set = models.ForeignKey(RuneSet, on_delete=models.PROTECT) # set
    upgrade_limit = 15 # upgrade_limit
    upgrade_curr = models.IntegerField(validators=[MinValueValidator(0),MaxValueValidator(upgrade_limit)]) #upgrade_curr
    base_value = models.IntegerField() # base_value
    sell_value = models.IntegerField() # sell_value

    primary = models.IntegerField(choices=RUNE_EFFECTS) # pri_eff[0]
    primary_value = models.IntegerField() # pri_eff[1]
    innate = models.IntegerField(choices=RUNE_EFFECTS) # prefix_eff[0]
    innate_value = models.IntegerField() # prefix_eff[1]
    substats = ArrayField( models.IntegerField(choices=RUNE_EFFECTS) ) # sec_eff[i][0]
    substats_values = ArrayField( models.IntegerField() ) # sec_eff[i][1]
    substats_grindstones = ArrayField( models.IntegerField() ) # sec_eff[i][2]
    substats_enchants = ArrayField( models.IntegerField() ) # sec_eff[i][3]

    quality_original = models.IntegerField(choices=RUNE_QUALITIES) # extra
    equipped = models.BooleanField() # occupied_type
    # ^ OR same as JSON (type, if type different than monster then id = 0)
    # ^ OR models.BigIntegerField 
    # ^ OR models.ForeignKey for Monster [what with Inventory then?]
    # ^ OR occupied as a Boolean variable and then Foreign Key with possibility of being NULL
    # ^ OR occupied as a Boolean variable and then Monster has its key in class, there is only info if occupied [then needs to make a Trigger]
    
    def __str__(self):
        return self.id