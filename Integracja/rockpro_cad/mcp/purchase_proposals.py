"""ROC-32: dated, quantity-aware purchase proposals; never places an order."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math

from material_service import digest, token
from inventory_service import get_inventory, quantity


def money(value):
    if type(value) not in (str,int,float,Decimal):raise ValueError('Explicit decimal monetary value required')
    result=Decimal(str(value))
    if not result.is_finite() or not 0<=result<=Decimal('1000000000'):raise ValueError('Invalid monetary value')
    return result


def monetary_text(value):return str(value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def iso(value):
    if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value:raise ValueError('ISO date required')
    return date.fromisoformat(value)


def calculate_purchases(requirements, inventory, offers, policy):
    if not isinstance(requirements,dict) or set(requirements)!={'scope','bindings','lines'}:raise ValueError('Exact purchase requirements required')
    if requirements['scope'] not in ('source_input','synthetic_test') or not isinstance(requirements['bindings'],list) or not requirements['bindings']:
        raise ValueError('Requirements need source bindings and scope')
    lines=requirements['lines']
    if not isinstance(lines,list) or not 1<=len(lines)<=1000:raise ValueError('Purchase requirement limit 1..1000')
    ids=set()
    for line in lines:
        if not isinstance(line,dict) or set(line)!={'id','item_id','unit','quantity','required_date'}:raise ValueError('Exact purchase line required')
        for k in ('id','item_id'):token(line[k],k)
        if line['id'] in ids:raise ValueError('Duplicate demand line')
        ids.add(line['id']);quantity(line['quantity']);iso(line['required_date'])
        if line['unit'] not in ('piece','sheet'):raise ValueError('Only complete pieces or explicitly dimensioned sheet SKU purchasing supported')
    if not isinstance(policy,dict) or set(policy)!={'as_of_date','currency','max_surplus_units','max_cash_gross','approved_substitutes'}:
        raise ValueError('Explicit dated cash/stock/substitution policy required')
    today=iso(policy['as_of_date']);currency=policy['currency']
    if not isinstance(currency,str) or len(currency)!=3 or not currency.isalpha() or currency!=currency.upper():raise ValueError('ISO currency code required')
    max_cash=money(policy['max_cash_gross'])
    if type(policy['max_surplus_units']) is not int or not 0<=policy['max_surplus_units']<=1000000:raise ValueError('Explicit surplus limit required')
    substitutes=policy['approved_substitutes']
    if not isinstance(substitutes,dict):raise ValueError('Approved substitution map required')
    for key,values in substitutes.items():
        token(key,'substitution source')
        if not isinstance(values,list) or len(values)>100:raise ValueError('Bounded substitution list required')
        for value in values:token(value,'approved substitute')
    if not isinstance(offers,list) or len(offers)>200:raise ValueError('Offer limit 200')
    supplies=[]
    for lot in inventory['lots']:
        if lot['scope']==requirements['scope'] and lot['condition']=='usable' and lot['free']>0:
            supplies.append(dict(id=lot['id'],item_id=lot['item_id'],unit=lot['unit'],quantity=lot['free'],date=policy['as_of_date'],kind='free_stock'))
    for delivery in inventory['deliveries']:
        if delivery['scope']==requirements['scope'] and delivery['outstanding']>0:
            supplies.append(dict(id=delivery['id'],item_id=delivery['item_id'],unit=delivery['unit'],quantity=delivery['outstanding'],date=delivery['due_date'],kind='confirmed_delivery'))
    supplies.sort(key=lambda s:(s['date'],s['kind'],s['id']))
    results=[]
    offer_fields={'id','item_id','unit','supplier','currency','quote_date','valid_until','pack_size','moq','lead_days','available_quantity','price_breaks','shipping_net','tax_percent'}
    for line in sorted(lines,key=lambda r:(r['required_date'],r['id'])):
        missing=line['quantity'];allocations=[]
        for supply in supplies:
            if supply['item_id']!=line['item_id'] or supply['unit']!=line['unit'] or supply['date']>line['required_date']:continue
            used=min(missing,supply['quantity'])
            if used:allocations.append(dict(supply_id=supply['id'],kind=supply['kind'],quantity=used,available_date=supply['date']))
            supply['quantity']-=used;missing-=used
        options=[];rejections=[]
        allowed={line['item_id'],*substitutes.get(line['item_id'],[])}
        for offer in offers:
            if not isinstance(offer,dict) or set(offer)!=offer_fields:raise ValueError('Exact offer fields required; use null for missing data')
            if offer['item_id'] not in allowed or offer['unit']!=line['unit']:continue
            token(offer['id'],'offer ID');token(offer['supplier'],'supplier')
            incomplete=[k for k in offer_fields if offer[k] is None]
            if incomplete:
                rejections.append(dict(offer_id=offer['id'],reason='incomplete_offer',missing_fields=sorted(incomplete)));continue
            if offer['currency']!=currency:
                rejections.append(dict(offer_id=offer['id'],reason='currency_conversion_not_configured'));continue
            quote=iso(offer['quote_date']);valid=iso(offer['valid_until'])
            if quote>today or valid<today:
                rejections.append(dict(offer_id=offer['id'],reason='quote_not_current'));continue
            quantity(offer['pack_size']);quantity(offer['moq'])
            if type(offer['lead_days']) is not int or not 0<=offer['lead_days']<=3650:raise ValueError('Calendar lead days required')
            if type(offer['available_quantity']) is not int or offer['available_quantity']<0:raise ValueError('Confirmed available quantity required')
            arrival=today+timedelta(days=offer['lead_days'])
            breaks=offer['price_breaks']
            if not isinstance(breaks,list) or not 1<=len(breaks)<=20:raise ValueError('Bounded price breaks required')
            tiers=[]
            for tier in breaks:
                if not isinstance(tier,dict) or set(tier)!={'min_quantity','unit_net'}:raise ValueError('Exact price tier required')
                quantity(tier['min_quantity']);tiers.append((tier['min_quantity'],money(tier['unit_net'])))
            if len({n for n,p in tiers})!=len(tiers):raise ValueError('Duplicate price tier')
            tiers.sort();shipping=money(offer['shipping_net']);tax=money(offer['tax_percent'])
            if tax>100:raise ValueError('Tax percentage exceeds 100')
            if not missing:continue
            quantities={math.ceil(max(missing,offer['moq'],tiers[0][0])/offer['pack_size'])*offer['pack_size']}
            quantities.update(math.ceil(max(missing,offer['moq'],n)/offer['pack_size'])*offer['pack_size'] for n,p in tiers)
            for n in sorted(quantities):
                price=[p for threshold,p in tiers if threshold<=n][-1]
                net=price*n+shipping;gross=(net*(1+tax/100)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                surplus=n-missing;reasons=[]
                if arrival>iso(line['required_date']):reasons.append('late_arrival')
                if n>offer['available_quantity']:reasons.append('insufficient_confirmed_availability')
                if surplus>policy['max_surplus_units']:reasons.append('surplus_limit')
                if gross>max_cash:reasons.append('cash_limit')
                options.append(dict(offer_id=offer['id'],supplier=offer['supplier'],item_id=offer['item_id'],
                    substitute=offer['item_id']!=line['item_id'],quantity=n,shortage=missing,surplus=surplus,
                    unit_net=str(price),shipping_net=monetary_text(shipping),total_net=monetary_text(net),
                    total_gross=monetary_text(gross),currency=currency,arrival_date=arrival.isoformat(),
                    feasible=not reasons,restrictions=reasons))
        options.sort(key=lambda o:(not o['feasible'],Decimal(o['total_gross']),o['surplus'],o['arrival_date'],o['offer_id']))
        results.append(dict(requirement=line,allocations=allocations,shortage=missing,options=options,
                            rejected_offers=rejections,preferred_option=next((o for o in options if o['feasible']),None)))
    result=dict(lines=results,bindings=requirements['bindings'],scope=requirements['scope'],
        input_sha256=digest(dict(requirements=requirements,inventory=inventory,offers=offers,policy=policy)),
        shipping_basis='per_requirement_offer; consolidated shipping not optimized',
        lead_time_basis='calendar_days',cash_limit_basis='per_option; combined cash not approved',
        proposal_only=True,orders_placed=False,production_approved=False)
    result['proposal_sha256']=digest(result)
    return result


def preview_purchases(requirements,offers,policy):
    return calculate_purchases(requirements,get_inventory(),offers,policy)
