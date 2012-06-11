import sys
import os
import re
import subprocess

def extract_csv(log, csvgz_file, write_status=None):
  log_modified = os.path.getmtime(log)
  entries = [ f for f in os.listdir(log) if re.search(".log.gz$", f) ]
  progress = 0
  if write_status != None:
    pid = str(os.getpid())
    file_path = os.path.join(write_status, pid + ".status")
    f = open(file_path, 'w')
    f.write(str(3 * len(entries)) + "\r\n")
    f.flush()

  def build_result(scenariokeys, scenario, key, value) :
    r = ''
    for k in scenariokeys:
      if k in scenario:
         r = r + str(scenario[k])
      else:
         r = r + "null"
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
      gunzip_process = subprocess.Popen(["gunzip", "-c", os.path.join(log, entry)], stdout=subprocess.PIPE)
      e = gunzip_process.stdout
      lines = e.readlines()
      e.close()
      gunzip_process.wait()
      for l in lines:
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

  csv_compressed = open(csvgz_file, 'w')
  gzip_process = subprocess.Popen(['gzip'], stdin=subprocess.PIPE, stdout=csv_compressed)
  csv = gzip_process.stdin

  for key in scenariokeys:
    csv.write(key + ',')

  csv.write('key,value\n')

  re_timedrun = re.compile("mkdir.*timedrun")
  re_err = re.compile('NullPointerException|JikesRVM: WARNING: Virtual processor has ignored timer interrupt|hardware trap|-- Stack --|code: -1|OutOfMemory|ArrayIndexOutOfBoundsException|FileNotFoundException|FAILED warmup|Validation FAILED')
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
    gunzip_process = subprocess.Popen(["gunzip", "-c", os.path.join(log, entry)], stdout=subprocess.PIPE)
    e = gunzip_process.stdout
    lines = e.readlines()
    e.close()
    gunzip_process.wait()
    line_count = len(lines)
    line = 0 
    while 1:
      # Read a line

      def eat_error(line):
        while 1:
          if line >= line_count or re_timedrun.search(lines[line]):
            break;
          line += 1
        return line

      if line >= line_count:
        break

      l = lines[line]

      if re_timedrun.search(l):
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
      elif re_err.search(l):
        error = 1
        line = eat_error(line)
        continue
      elif l.startswith('='):
        m = re_scenario.match(l)
        if m:
          scenario[m.group(1)] = m.group(2)
        elif re_tabulate.match(l):
          headerline = lines[line+1]
          dataline = lines[line+2]
          line += 2
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
            line = eat_error(line)
            continue
        elif re_mmtkstats.match(l):
          headerline = lines[line+1]
          dataline = lines[line+2]
          line += 2
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
            line = eat_error(line)
            continue
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
      line += 1

    if subentry >= 0 and error == 0:
      for r in results:
        csv.write(r)
    progress += 2 
    if write_status != None:
      f.write(str(progress) + "\r\n")
      f.flush()

  csv.close()
  gzip_process.wait()
  csv_compressed.close()
  if write_status != None:
    f.close()

  os.utime(csvgz_file, (-1, log_modified))

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print "Usage: python Tabulate.py log-folder csv-file [status-dir]"
        sys.exit(1)
    
    print "Tabulating %s to %s (pid %d)" % (sys.argv[1], sys.argv[2], os.getpid())
    if len(sys.argv) == 3:
      extract_csv(sys.argv[1], sys.argv[2])
    else:
      extract_csv(sys.argv[1], sys.argv[2], sys.argv[3])
