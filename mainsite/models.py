from django.db import models

class AdvancedManager(models.Manager):
    """Contains advanced functions, but nothing related to StandardLookup tables, such as get_if_exist(**kwargs)"""
    
    def get_if_exist(self, **kwargs):
        """Returns the matching object if it uniquely exists, None otherwise"""
        try:
            return self.get(**kwargs)
        except (self.model.DoesNotExist, self.model.MultipleObjectsReturned) as e:
            return None
    


class BaseModel(models.Model):
    objects = AdvancedManager()
    
    class Meta:
        abstract        = True


class I18nString(BaseModel):
    fr_fr = models.CharField(max_length=9999, null=True)
    en_us = models.CharField(max_length=9999, null=True)
    
    def __unicode__(self):
        return unicode(self.fr_fr)

class Job(BaseModel):
    name = models.ForeignKey(I18nString, related_name="job_name")
    
    def __unicode__(self):
        return unicode(self.name)

class ItemCategory(BaseModel):
    name = models.ForeignKey(I18nString, related_name="itemcategory_name")
    
    def __unicode__(self):
        return unicode(self.name)

class ItemType(BaseModel):
    name = models.ForeignKey(I18nString)
    category = models.ForeignKey(ItemCategory)
    job = models.ForeignKey(Job, related_name="itemcategory_job", null=True)
    
    def __unicode__(self):
        return unicode(self.name)

class Attribute(BaseModel):
    name = models.ForeignKey(I18nString)
    
    def __unicode__(self):
        return unicode(self.name)

class Item(BaseModel):
    name                = models.ForeignKey(I18nString, related_name="item_name")
    description         = models.ForeignKey(I18nString, related_name="item_description", null=True)
    icon                = models.CharField(max_length=255, null=True)
    item_type           = models.ForeignKey(ItemType, null=True)
    level               = models.IntegerField(null=True)
    attributes          = models.ManyToManyField(Attribute, related_name="item_attributes", through='AttributeValue', null=True)
    craft               = models.ManyToManyField("Item", through='Recipe', symmetrical=False, null=True)
    has_valid_recipe    = models.BooleanField(default="True")
    conditions          = models.ManyToManyField(Attribute, related_name="item_condition", through='AttributeCondition', null=True)
    cost                = models.IntegerField(null=True)
    range               = models.IntegerField(null=True)
    crit_chance         = models.IntegerField(null=True)
    crit_damage         = models.IntegerField(null=True)
    failure             = models.IntegerField(null=True)
    
    def __unicode__(self):
        return unicode(self.name)

class AttributeValue(BaseModel):
    item = models.ForeignKey(Item)
    attribute = models.ForeignKey(Attribute)
    min_value = models.IntegerField()
    max_value = models.IntegerField()
    
    def __unicode__(self):
        return unicode(self.item) + "-" + unicode(self.attribute)

class AttributeCondition(BaseModel):
    item = models.ForeignKey(Item)
    attribute = models.ForeignKey(Attribute)
    equality = models.CharField(max_length=1)
    required_value = models.IntegerField()
    
    def __unicode__(self):
        return unicode(self.item) + "-" + unicode(self.attribute)

class Recipe(BaseModel):
    item = models.ForeignKey(Item, related_name="recipe_item")
    element = models.ForeignKey(Item, related_name="recipe_element")
    quantity = models.IntegerField()
    
    def __unicode__(self):
        return unicode(self.item) + " " + str(self.quantity) + "x" + unicode(self.element)


