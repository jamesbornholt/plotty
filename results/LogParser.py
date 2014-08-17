import re
import string
import sys
import subprocess
import gzip
import os

# Extract scenario
re_filename = re.compile("^(\w+)\.(\d+)\.(\d+)\.([a-zA-Z0-9_\-\.\:\,]+)\.log\.gz$")
re_notdigit = re.compile("^[0-9]")
re_scenario_kv = re.compile("^([^-]*)-(.*)$")
# Parsing
re_scenario = re.compile("====> Scenario (.*)=(.*)$")
re_timedrun = re.compile("mkdir.*timedrun")
re_err = re.compile('NullPointerException|JikesRVM: WARNING: Virtual processor has ignored timer interrupt|hardware trap|-- Stack --|code: -1|OutOfMemory|ArrayIndexOutOfBoundsException|FileNotFoundException|FAILED warmup|Validation FAILED|caught alarm')
re_tabulate = re.compile("============================ Tabulate Statistics ============================")
re_mmtkstats = re.compile("============================ MMTk Statistics Totals ============================")
re_nonwhitespace = re.compile("\S+")
re_whitespace = re.compile("\s+")
re_digit = re.compile("\d+")
re_starting = re.compile("=====(==|) .* (S|s)tarting")
re_passed = re.compile("PASSED in (\d+) msec")
re_warmup = re.compile("completed warmup \d* *in (\d+) msec")
re_finished = re.compile("Finished in (\S+) secs")
re_998 = re.compile("_997_|_998_")

# parser states
class states(object):
    NOTHING = 0
    IN_INVOCATION = 1
    IN_TABULATE_STATS_HEADER = 10
    IN_TABULATE_STATS_DATA = 11
    IN_MMTK_STATS_HEADER = 20
    IN_MMTK_STATS_DATA = 21
    IN_ERROR = 30

# a "Result" is a single iteration of a benchmark invocation
class Result(object):
    def __init__(self, scenario, value):
        self.scenario = scenario
        self.value = value

def extract_scenario(scenario, entry):
    """ Extract scenario variables from a log filename """
    m = re_filename.match(entry)
    scenario["benchmark"] = m.group(1)
    scenario["hfac"] = m.group(2)
    scenario["heap"] = m.group(3)
    scenario["buildstring"] = m.group(4)
    buildparams = scenario["buildstring"].split(".")
    scenario["build"] = buildparams[0]
    for p in buildparams[1::]:
        if not re_notdigit.match(p):
            m = re_scenario_kv.match(p)
            if m:
                scenario[m.group(1)] = m.group(2)
            else:
                scenario[p] = 1

def parse_csv(logpath, filename):
    """ Parse a single logfile. We assume the logfile is gzipped. """

    # Results
    results = list()

    # Initialise parsing state
    state = states.NOTHING

    iteration = 0
    scenario = dict()
    value = []
    invocation_results = list()  # results for this invocation (n iterations in a single invocation)

    legacy_mode = True
    legacy_invocation = 0
    legacy_scenario = {}

    tabulate_stats_headers = list()
    mmtk_stats_headers = list()

    n = 0  # lines

    # Open the file for reading
    f = gzip.open(os.path.join(logpath, filename), "r")

    # Read one line at a time
    for l in f:
        n += 1

        if state == states.IN_INVOCATION:
            # Is this line some sort of data output?
            if l[0] == '=':
                m = re_scenario.match(l)
                if m:
                    legacy_mode = False
                    scenario[m.group(1)] = m.group(2)
                elif re_starting.match(l):
                    # It's the start of a new iteration, wrap up the last
                    # if we've gathered data
                    if len(value) > 0:
                        # r = DataRow()
                        if legacy_mode:
                            if not legacy_scenario:
                                extract_scenario(legacy_scenario, filename)
                            scenario.update(legacy_scenario)
                            scenario['invocation'] = legacy_invocation
                        r = Result(scenario, value)
                        invocation_results.append(r)
                        iteration = iteration + 1
                        scenario = dict(scenario)
                        scenario["iteration"] = iteration
                        value = []
                elif re_tabulate.match(l):
                    state = states.IN_TABULATE_STATS_HEADER
                elif re_mmtkstats.match(l):
                    state = states.IN_MMTK_STATS_HEADER
                else:
                    m = re_passed.search(l)
                    if m:
                        # it's a PASSED result line
                        value.append(("bmtime", m.group(1)))
                        continue
                    m = re_warmup.search(l)
                    if m:
                        # it's a warmup pass
                        value.append(("bmtime", m.group(1)))
                        continue
                    m = re_finished.search(l)
                    if m and not re_998.search(l):
                        msec = float(m.group(1)) * 1000.0
                        value.append(("bmtime", str(msec)))
                        continue

                    # Now check for errors
                    if re_err.search(l):
                        state = states.IN_ERROR

            # Have we finished an invocation?
            elif re_timedrun.match(l):
                # Start of a new invocation, finalise this one (wrap up the
                # last iteration if necessary)
                if len(value) > 0:
                    # r = DataRow()
                    if legacy_mode:
                        if not legacy_scenario:
                            extract_scenario(legacy_scenario, filename)
                        scenario.update(legacy_scenario)
                        scenario['invocation'] = legacy_invocation
                    r = Result(scenario, value)
                    invocation_results.append(r)
                results.extend(invocation_results)
                invocation_results = list()
                scenario = dict()
                value = []
                iteration = 0
                scenario['iteration'] = iteration
                legacy_invocation += 1

            # Or is this line an error?
            elif re_err.search(l):
                state = states.IN_ERROR

        elif state == states.IN_ERROR:
            # skip until next re_timedrun
            if re_timedrun.match(l):
                invocation_results = list()
                scenario = dict()
                value = []
                iteration = 0
                scenario['iteration'] = iteration
                legacy_invocation += 1  # Make sure the invocation count is right
                state = states.IN_INVOCATION

        elif state == states.IN_TABULATE_STATS_HEADER:
            # next line should be a list of headers; check it's valid
            if re_nonwhitespace.match(l):
                tabulate_stats_headers = map(string.strip, re_whitespace.split(l))
                state = states.IN_TABULATE_STATS_DATA
            else:
                # not valid
                state = IN_ERROR

        elif state == states.IN_TABULATE_STATS_DATA:
            # next line should be a list of data
            if re_digit.match(l):
                vals = re_whitespace.split(l)
                if len(vals) != len(tabulate_stats_headers):
                    state = states.IN_ERROR
                    continue
                for k, v in zip(tabulate_stats_headers, vals):
                    if k == '':
                        continue
                    value.append((k, v))
                state = states.IN_INVOCATION
            else:
                state = states.IN_ERROR

        elif state == states.IN_MMTK_STATS_HEADER:
            # next line should be a list of headers; check it's valid
            if re_nonwhitespace.match(l):
                tabulate_stats_headers = map(string.strip, re_whitespace.split(l))
                state = states.IN_MMTK_STATS_DATA
            else:
                # not valid
                state = states.IN_ERROR

        elif state == states.IN_MMTK_STATS_DATA:
            # next line should be a list of data
            if re_digit.match(l):
                vals = re_whitespace.split(l)
                if len(vals) != len(tabulate_stats_headers):
                    state = IN_ERROR
                    continue
                totaltime = 0.0
                for k, v in zip(tabulate_stats_headers, vals):
                    if k == '':
                        continue
                    if k == 'time.mu' or k == 'time.gc':
                        totaltime += float(v)
                    value.append((k,v))
                value.append(("time", str(totaltime)))
                state = states.IN_INVOCATION
            else:
                state = states.IN_ERROR

        elif state == states.NOTHING:
            # Find an invocation
            if re_timedrun.match(l):
                # Found an invocation
                state = states.IN_INVOCATION
                scenario['iteration'] = iteration
        # end of state switch
    # end of line loop

    # Write the last set of results, if we didn't finish with an error
    if state == states.IN_INVOCATION:
        if len(value) > 0:
            if legacy_mode:
                if not legacy_scenario:
                    extract_scenario(legacy_scenario, filename)
                scenario.update(legacy_scenario)
                scenario['invocation'] = legacy_invocation
            r = Result(scenario, value)
            invocation_results.append(r)
        results.extend(invocation_results)

    f.close()

    return results

def tabulate_log_folder(logpath, outfile, write_status=None):
    files = [f for f in os.listdir(logpath) if f[-7:] == '.log.gz']

    if write_status:
        progress = 0
        pid = str(os.getpid())
        status_path = os.path.join(write_status, pid + ".status")
        status_file = open(status_path, 'w')
        status_file.write("%d\r\n" % (len(files)+1))
        status_file.flush()

    results = []
    for filename in files:
        r = parse_csv(logpath, filename)
        results.extend(r)
        if write_status:
            progress += 1
            status_file.write("%d\r\n" % progress)
            status_file.flush()

    # Sort the scenario headers
    scenario_headers = set()
    for r in results:
        for k in r.scenario.keys():
            if k not in scenario_headers:
                scenario_headers.add(k)
    scenario_headers_sorted = list(scenario_headers)
    scenario_headers_sorted.sort()

    # Open the output file
    csv_file = open(outfile, 'w')
    gzip_process = subprocess.Popen(['gzip'], stdin=subprocess.PIPE, stdout=csv_file, bufsize=-1)
    csv_out = gzip_process.stdin

    # Print the header row
    for k in scenario_headers_sorted:
        csv_out.write(k)
        csv_out.write(",")
    csv_out.write("key,value\n")

    # Print each result (note: one Result object is more than one CSV line)
    for r in results:
        scenario_str = ""
        for k in scenario_headers_sorted:
            if k in r.scenario:
                scenario_str += str(r.scenario[k])
            else:
                scenario_str += "null"
            scenario_str += ","
        for key, val in r.value:
            csv_out.write(scenario_str)
            csv_out.write(key + "," + val)
            csv_out.write("\n")

    csv_out.close()
    gzip_process.wait()
    csv_file.close()

    # Now signal that we're finished
    if write_status:
        progress += 1
        status_file.write("%d\r\n" % progress)
        status_file.close()

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print "Usage: python LogParser.py log-folder csv-file [status-dir]"
        sys.exit(1)

    print "Parsing %s to %s (pid %d)" % (sys.argv[1], sys.argv[2], os.getpid())
    if len(sys.argv) == 3:
        tabulate_log_folder(sys.argv[1], sys.argv[2])
    else:
        tabulate_log_folder(sys.argv[1], sys.argv[2], sys.argv[3])
