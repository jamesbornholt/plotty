import os, csv, datetime
from results.models import *

def doimport(path, name, console=False):
    try:
        count = 0
        
        log = Log()
        log.Name = name
        log.Date = datetime.datetime.now()
        log.save()
        
        scenarios = {}
        
        reader = csv.DictReader(open(path, 'rb'))
        for row in reader:
            result = Result()
            result.Invocation = row['invocation']
            result.Key = row['key']
            result.Value = row['value']
            result.Log = log
            
            scenariohash = hash_scenario(row)
            if scenariohash not in scenarios:
                scenarios[scenariohash] = create_scenario(row, log)
            result.Scenario = scenarios[scenariohash]

            result.save()
            
            count += 1
            
            if console and count % 1000 == 0:
                print "  %d results..." % count
                
        return count
    except OverflowError:
        return 0
    
def hash_scenario(row):
    hashstr = ""
    for key in row:
        if key not in ['invocation', 'key', 'value']:
            hashstr += key + row[key]
    return hashstr
    
def create_scenario(row, log):
    scvars = set()
    scen = Scenario()
    scen.Log = log
    scen.save()
    
    for key in row:
        if key not in ['invocation', 'key', 'value']:
            var = ScenarioVar()
            var.Key = key
            var.Value = row[key]
            var.Log = log
            var.Scenario = scen
            var.save()
            scvars.add(var)
    
    scen.Columns.add(*scvars)

    return scen
