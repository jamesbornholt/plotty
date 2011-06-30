import sys
import os
import re
import gzip

def extract_csv(log, csv_file, write_status=None):
  entries = [ f for f in os.listdir(log) if re.search(".log.gz$", f) ]
  progress = 0
  if write_status != None:
    pid = str(os.getpid())
    file_path = os.path.join(write_status, pid + ".status")
    f = open(file_path, 'w')
    f.write(str(2 * len(entries)) + "\r\n")
    f.flush()

  def build_result(scenariokeys, scenario, key, value) :
    r = ''
    for k in scenariokeys:
      if k in scenario:
         r = r + str(scenario[k])
      r = r + ','
    r = r + key + ',' + str(value) + '\n'
    return r

  re_filename = re.compile("^(\w+)\.(\d+)\.(\d+)\.([a-zA-Z0-9_\-\.]+)\.log\.gz$")
  re_notdigit = re.compile("^[0-9]")
  re_scenario_kv = re.compile("^([^-]*)-(.*)$")
  def extract_scenario(scenario, entry):
    m = re_filename.match(entry)
    scenario["benchmark"] = m.group(1)
    scenario["hfac"] = m.group(2)
    scenario["heap"] = m.group(3)
    scenario["buildstring"] = m.group(4)
    buildparams = scenario["buildstring"].split(".") 
    scenario["build"] = buildparams[0]
    for p in buildparams[1::] :
      if not re_notdigit.match(p):
        m = re_scenario_kv.match(p)
        if m:
          scenario[m.group(1)] = m.group(2)
        else:
          scenario[p] = 1

  # Build the set of unique scenario keys
  legacy_mode = True
  legacy_scenario = dict()
  scenario = dict()
  scenario['iteration'] = 1
  legacy_scenario['iteration'] = 1
  legacy_scenario['invocation'] = 1

  re_scenario = re.compile("====> Scenario (.*)=(.*)$")

  for entry in entries:
      extract_scenario(legacy_scenario, entry)
      e = gzip.open(os.path.join(log, entry), 'r')
      for l in e:
        m = re_scenario.match(l)
        if (m):
          legacy_mode = False
          scenario[m.group(1)] = 1
      progress += 1
      if write_status != None:
        f.write(str(progress) + "\r\n")
        f.flush()

  if legacy_mode:
    scenariokeys = legacy_scenario.keys()
  else:
    scenariokeys = scenario.keys()

  csv = open(csv_file, 'w')

  for key in scenariokeys:
    csv.write(key + ',')

  csv.write('key,value\n')

  re_timedrun = re.compile("mkdir.*timedrun")
  re_err = re.compile('NullPointerException|JikesRVM: WARNING: Virtual processor has ignored timer interrupt|hardware trap|-- Stack --|code: -1|OutOfMemory|ArrayIndexOutOfBoundsException|FileNotFoundException|FAILED warmup')
  re_tabulate = re.compile("============================ Tabulate Statistics ============================")
  re_mmtkstats = re.compile("============================ MMTk Statistics Totals ============================")
  re_nonwhitespace = re.compile("\S+")
  re_whitespace = re.compile("\s+")
  re_digit = re.compile("\d+")
  re_passed = re.compile("PASSED in (\d+) msec")
  re_warmup = re.compile("completed warmup \d* *in (\d+) msec")
  re_finished = re.compile("Finished in (\S+) secs")
  re_998 = re.compile("_997_|_998_")

  for entry in entries:
    invocation = 0
    subentry = -1
    error = 0
    e = gzip.open(os.path.join(log, entry), 'r')
    while 1:
      l = e.readline()
      if not l:
        break
      m = re_scenario.match(l)
      if m:
        scenario[m.group(1)] = m.group(2)
      elif re_timedrun.search(l):
        if subentry >= 0 and error == 0:
          for r in results:
            csv.write(r)
        iteration = 0
        scenario = dict()
        if legacy_mode:
          scenario["invocation"] = invocation
          extract_scenario(scenario, entry)
          invocation += 1
        results = list()
        scenario['iteration'] = iteration
        error = 0
        subentry = subentry + 1
      elif error == 0:
        if re_err.search(l):
            error = 1
        else:
          if re_tabulate.match(l):
            headerline = e.readline()
            dataline = e.readline()
            if re_nonwhitespace.match(headerline) and re_digit.match(dataline):
              keys = re_whitespace.split(headerline)
              vals = re_whitespace.split(dataline)
              for key in keys:
                key = key.strip()
                val = vals.pop(0)
                if not key == '':
                  results.append(build_result(scenariokeys, scenario, key, val))
            else:
              error = 1
          elif re_mmtkstats.match(l):
            headerline = e.readline()
            dataline = e.readline()
            if re_nonwhitespace.match(headerline) and re_digit.match(dataline):
              keys = re_whitespace.split(headerline)
              vals = re_whitespace.split(dataline)
              totaltime = 0.0
              for key in keys:
                val = vals.pop(0)
                if key == 'time.mu' or key == 'time.gc':
                  totaltime = float(totaltime) + float(val)
                if not key == '':
                  results.append(build_result(scenariokeys, scenario, key, val))
              results.append(build_result(scenariokeys, scenario, 'time', totaltime))
            else:
              error = 1
          else:
            m = re_passed.search(l)
            if m:
              results.append(build_result(scenariokeys, scenario, "bmtime", m.group(1)))
              iteration = iteration + 1
              scenario["iteration"] = iteration
            else:
              m = re_warmup.search(l)
              if m:
                results.append(build_result(scenariokeys, scenario, "bmtime", m.group(1)))
                iteration = iteration + 1
                scenario["iteration"] = iteration
              else:
                m = re_finished.search(l)
                if m and not re_998.search(l):
                  msec = float(m.group(1)) * 1000.0
                  results.append(build_result(scenariokeys, scenario, "bmtime", msec))
                  iteration = iteration + 1
                  scenario["iteration"] = iteration
    e.close()
    if subentry >= 0 and error == 0:
      for r in results:
        csv.write(r)
    progress += 1
    if write_status != None:
      f.write(str(progress) + "\r\n")
      f.flush()

  csv.close()
  if write_status != None:
    f.close()

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print "Usage: python Tabulate.py log-folder csv-file [status-dir]"
        sys.exit(1)
    
    print "Tabulating %s to %s (pid %d)" % (sys.argv[1], sys.argv[2], os.getpid())
    if len(sys.argv) == 3:
      extract_csv(sys.argv[1], sys.argv[2])
    else:
      extract_csv(sys.argv[1], sys.argv[2], sys.argv[3])
