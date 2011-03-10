import sys
import os
import re
import gzip

def extract_csv(log, write_status=None):
  entries = [ f for f in os.listdir(log) if re.search(".log.gz$", f) ]
  progress = 0
  if write_status != None:
    pid = str(os.getpid())
    file_path = os.path.join(write_status, pid + ".status")
    f = open(file_path, 'w')
    f.write(str(len(entries)) + "\r\n")
    f.flush()

  def build_result(scenariokeys, scenario, key, value) :
    r = ''
    for k in scenariokeys:
      if k in scenario:
         r = r + str(scenario[k])
      r = r + ','
    r = r + key + ',' + str(value) + '\n'
    return r

  # Build the set of unique scenario keys
  scenario = dict()
  scenario['iteration'] = 1
  for entry in entries:
      e = gzip.open(os.path.join(log, entry), 'r')
      for l in e:
        m = re.match("====> Scenario (.*)=(.*)$", l)
        if (m):
          scenario[m.group(1)] = 1

  scenariokeys = scenario.keys()

  csv = open(log + '.csv', 'w')

  for key in scenariokeys:
    csv.write(key + ',')

  csv.write('key,value\n')

  for entry in entries:
    subentry = -1
    error = 0
    e = gzip.open(os.path.join(log, entry), 'r')
    while 1:
      l = e.readline()
      if not l:
        break
      m = re.match("====> Scenario (.*)=(.*)$", l)
      if m:
        scenario[m.group(1)] = m.group(2)
      elif re.search('mkdir.*timedrun', l):
        if subentry >= 0 and error == 0:
          for r in results:
            csv.write(r)
        iteration = 0
        scenario = dict()
        results = list()
        scenario['iteration'] = iteration
        error = 0
        subentry = subentry + 1
      elif error == 0:
        if re.search('NullPointerException|JikesRVM: WARNING: Virtual processor has ignored timer interrupt|hardware trap|-- Stack --|code: -1|OutOfMemory|ArrayIndexOutOfBoundsException|FileNotFoundException|FAILED warmup', l):
            error = 1
        else:
          if re.match("============================ Tabulate Statistics ============================", l):
            headerline = e.readline()
            dataline = e.readline()
            if re.match("\S+",headerline) and re.match("\d+", dataline):
              keys = re.split("\s+", headerline)
              vals = re.split("\s+", dataline)
              for key in keys:
                val = vals.pop(0)
            else:
              error = 1
          elif re.match("============================ MMTk Statistics Totals ============================", l):
            headerline = e.readline()
            dataline = e.readline()
            if re.match("\S+",headerline) and re.match("\d+", dataline):
              keys = re.split("\s+", headerline)
              vals = re.split("\s+", dataline)
              totaltime = 0.0
              for key in keys:
                val = vals.pop(0)
                if key == 'time.mu' or key == 'time.gc':
                  totaltime = float(totaltime) + float(val)
                results.append(build_result(scenariokeys, scenario, key, val))
              results.append(build_result(scenariokeys, scenario, 'time', totaltime))
            else:
              error = 1
          else:
            m = re.search("PASSED in (\d+) msec",l)
            if m:
              results.append(build_result(scenariokeys, scenario, "bmtime", m.group(1)))
              iteration = iteration + 1
              scenario["iteration"] = iteration
            else:
              m = re.search("completed warmup \d* *in (\d+) msec",l)
              if m:
                results.append(build_result(scenariokeys, scenario, "bmtime", m.group(1)))
                iteration = iteration + 1
                scenario["iteration"] = iteration
              else:
                m = re.search("Finished in (\S+) secs",l)
                if m and not re.search("_997_|_998_",l):
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
    if len(sys.argv) < 2:
        print "Usage: python Tabulate.py log-folder [status-dir]"
        sys.exit(1)
    
    print "Tabulating %s (pid %d)" % (sys.argv[1], os.getpid())
    if len(sys.argv) < 3:
      extract_csv(sys.argv[1])
    else:
      extract_csv(sys.argv[1], sys.argv[2])