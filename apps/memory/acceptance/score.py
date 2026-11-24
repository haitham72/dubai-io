import json,sys
d=json.load(open(sys.argv[1]+'/s2_extract_cost.json',encoding='utf-8'))
c=d['changes'];print('sup',c['superseded_ok'],'ended',c['ended_ok'],'late',c['late_ok'],'rej',d['jobs']['rejected'] if isinstance(d['jobs']['rejected'],int) else d['jobs']['rejected'],'fp',d['privacy']['clean_gold_fp_pct'],'cost',d['cost_per_owner_day']['mean_usd'])
for k in ('superseded_details','ended_details','late_details'):
    for x in c[k]:
        if not x['ok']: print(' MISS',k,x)
