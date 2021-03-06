import json, logging, re

log = logging.getLogger(__name__)

from django.shortcuts import render_to_response
from django.template import RequestContext, loader
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

from mainsite.models import Attribute, ItemCategory, ItemType, Item, Panoplie, UpdateHistory, InvalidItem

EXCLUDE_CATEGORY = ["Ressource"]
RECIPE_SIZE_TO_JOB_LEVEL = {
    1: 1,
    2: 1,
    3: 10,
    4: 20,
    5: 40,
    6: 60,
    7: 80,
    8: 100
}

PAGE_TITLE = "Dofus: Outil de recherche d'objets"
PAGE_DESCRIPTION = "Outil de recherche d'objet pour le MMORPG Dofus."

def maintenance(request):
    return render_to_response("maintenance.html", context_instance=RequestContext(request))

def search(request):
    # Do not get attributes that are used only as condition
    attributes = Attribute.objects.filter(attributevalue__isnull=False).distinct().order_by("name")
    categories = ItemCategory.objects.all()
    last_update = UpdateHistory.objects.all().order_by("-started")[0].started
    
    page_parameters = {
        "attributes": attributes,
        "categories": categories,
        "pageTitle": PAGE_TITLE,
        "pageDescription": PAGE_DESCRIPTION,
        "pageUrl": request.build_absolute_uri(),
        "active_tab": "search",
        "udpate_time": last_update,
    }
    
    if not request.GET:
        return render_to_response("search.html", page_parameters, context_instance=RequestContext(request))
    
    
    types = request.GET.getlist("type")
    type_query = Q()
    type_query_pano = Q()
    
    for item_type in types:
        type_query |= Q(type=ItemType.objects.get(name=item_type))
        type_query_pano |= Q(item__type=ItemType.objects.get(name=item_type))
    
    
    name = request.GET.get("name")
    name_query = Q()
    if name:
        name_query = Q(name__icontains=name)
    
    
    level_min = get_int_or_default(request.GET.get("level-min"), 1)
    level_max = get_int_or_default(request.GET.get("level-max"), 200)
    
    level_query = Q(level__gte=level_min,level__lte=level_max)
    level_query_pano = Q(item__level__gte=level_min, item__level__lte=level_max)
    
    
    recipes = request.GET.getlist("recipe")
    recipe_query = Q()
    for recipe in recipes:
        recipe_query |= Q(recipe__size=recipe)
    
    
    cost_min = get_int_or_default(request.GET.get("cost-min"), 0)
    cost_max = get_int_or_default(request.GET.get("cost-min"), 100)
    
    cost_query = Q(cost__gte=cost_min,cost__lte=cost_max)
    cost_query_pano = Q(item__cost__gte=level_min, item__cost__lte=level_max)
    
    if cost_min == 0:
        cost_query |= Q(cost__isnull=True)
        cost_query_pano |= Q(item__cost__isnull=True)
    
    
    range_min = get_int_or_default(request.GET.get("range-min"), 0)
    range_max = get_int_or_default(request.GET.get("range-max"), 100)
    
    range_query = Q(range_min__gte=range_min,range_max__lte=range_max)
    range_query_pano = Q(item__range_min__gte=level_min, item__range_max__lte=level_max)
    
    if range_min == 0:
        range_query |= Q(range_min__isnull=True)
        range_query_pano |= Q(item__range_min__isnull=True)
    if range_max == 100:
        range_query |= Q(range_max__isnull=True)
        range_query_pano |= Q(item__range_max__isnull=True)
    
    attribute_querys = []
    attribute_querys_pano = []
    for k, v in request.GET.items():
        if re.match("attribute-\d+", k):
            index = k[10:]
            value_min = get_int_or_default(request.GET.get("value-min-"+index), 1)
            value_max = get_int_or_default(request.GET.get("value-max-"+index), 9999)
            
            attributeObject = Attribute.objects.get_if_exist(name=v)
            
            if not attributeObject:
                continue
            
            attribute_querys.append(Q(attributevalue__attribute=attributeObject,
                                      attributevalue__min_value__lte=value_max,
                                      attributevalue__max_value__gte=value_min))
            
            attribute_querys_pano.append(Q(panoplieattribute__attribute=attributeObject,
                                           panoplieattribute__value__lte=value_max,
                                           panoplieattribute__value__gte=value_min))
        
    
    items = Item.objects.filter(type_query & name_query & level_query & recipe_query & cost_query & range_query)
    for q in attribute_querys:
        items = items.filter(q)
    items = items.distinct().order_by("level")
    
    log.debug(type_query)
    log.debug(name_query)
    log.debug(level_query)
    log.debug(recipe_query)
    log.debug(attribute_querys)
    log.debug(items)
    
    
    
    panoplies = []
    if request.GET.get("include-panoplie") and not recipes:
        panoplies = Panoplie.objects.filter(name_query & type_query_pano & level_query_pano & cost_query_pano & range_query_pano)
        for q in attribute_querys_pano:
            panoplies = panoplies.filter(q)
        panoplies = panoplies.distinct()
        
        log.debug(type_query_pano)
        log.debug(name_query)
        log.debug(level_query_pano)
        log.debug(attribute_querys_pano)
        log.debug(panoplies)
        
    
    
    objects = [dictify_item(item) for item in items] + [dictify_pano(pano) for pano in panoplies]
    
    if "html" in request.META.get("PATH_INFO"):
        page_parameters.update({"objects": objects,})
        return render_to_response("search.html", page_parameters, context_instance=RequestContext(request))
    
    return HttpResponse(json.dumps(objects), mimetype="application/json");
    

def dictify_item(item):
    result = {}
    result["is_item"] = True
    result["name"] = item.name
    result["image"] = item.image
    result["description"] = item.description
    result["original_id"] = item.original_id
    result["type"] = item.type.name
    result["is_weapon"] = item.type.category.name == "Arme"
    result["level"] = item.level
    result["cost"] = item.cost
    result["range_min"] = item.range_min
    result["range_max"] = item.range_max
    result["crit_chance"] = item.crit_chance
    result["crit_damage"] = item.crit_damage
    result["failure"] = item.failure
    result["job"] = ""
    if item.type.job:
        result["job"] = item.type.job.name
        
    result["job_level"] = 0
    result["recipe"] = ""
    if item.recipe:
        result["job_level"] = RECIPE_SIZE_TO_JOB_LEVEL.get(item.recipe.size)
        result["recipe"] = item.recipe.text
    
    attributes = []
    for a in item.attributevalue_set.all().order_by("attribute__name"):
        if a.min_value != a.max_value:
            attributes.append(str(a.min_value) + " - " + str(a.max_value) + " " + a.attribute.name)
        else:
            attributes.append(str(a.min_value) + " " + a.attribute.name)
    result["attributes"] = attributes
    
    conditions = []
    for c in item.attributecondition_set.all().order_by("attribute__name"):
        conditions.append(c.attribute.name + " " + c.equality + " " + str(c.required_value))
    
    result["conditions"] = conditions
    
    if item.panoplie:
        result["panoplie"] = item.panoplie.name
    
    if InvalidItem.objects.filter(item=item).count() > 0:
        result["invalid"] = True
    
    return result

def dictify_pano(pano):
    result = {}
    result["is_item"] = False
    result["name"] = pano.name
    
    attributes = {}
    for a in pano.panoplieattribute_set.all().order_by("attribute__name"):
        if not attributes.has_key(a.no_of_items):
            attributes[a.no_of_items] = []
        
        attributes[a.no_of_items].append(str(a.value) + " " + a.attribute.name)
    
    result["attributes"] = attributes
    
    result["items"] = list(pano.item_set.all().values_list('name', flat=True))
    result["level"] = max(pano.item_set.values_list("level", flat=True))
    
    if InvalidItem.objects.filter(panoplie=pano).count() > 0:
        result["invalid"] = True
    
    return result

def get_int_or_default(string, default=0):
    try:
        return int(string)
    except:
        return default



def get_item(request):
    name = request.GET.get("name");
    
    result = {}
    
    if name:
        item = Item.objects.get_if_exist(name__iexact=name)
        pano = Panoplie.objects.get_if_exist(name__iexact=name)
        if item:
            result["isPanoplie"] = False
            result["html"] = loader.render_to_string("item.html", {"item": dictify_item(item), "hide_extra":True}, context_instance=RequestContext(request))
        elif pano:
            result["isPanoplie"] = True
            result["html"] = loader.render_to_string("pano.html", {"pano": dictify_pano(pano), "hide_extra":True}, context_instance=RequestContext(request))
    
    return HttpResponse(json.dumps(result), mimetype="application/json")


def flag_invalid(request):
    name = request.GET.get("name")
    item = Item.objects.get_if_exist(name=name)
    pano = Panoplie.objects.get_if_exist(name=name)
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    if item and InvalidItem.objects.filter(item=item).count() == 0:
        InvalidItem.objects.create(item=item, flag_date=timezone.now(), origin=ip)
        
    elif pano and InvalidItem.objects.filter(panoplie=pano).count() == 0:
        InvalidItem.objects.create(panoplie=pano, flag_date=timezone.now(), origin=ip)
    
    return HttpResponse()



