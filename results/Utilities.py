import math

def scenario_hash(scenario, exclude=None, include=None):
    """ Hashes a scenario dictionary by either including or excluding values
        based on the specified lists.
    """
    from plotty.results.DataTypes import ScenarioValue
    hashstr = ""
    i = 0
    for key in sorted(scenario):
        val = scenario[key]
        if isinstance(val, ScenarioValue):
            val = val.value
        i += 1
        hashstr += str(i)
        if exclude <> None and key not in exclude:
            hashstr += str(key) + str(val)
        elif include <> None and key in include:
            hashstr += str(key) + str(val)
        elif include == None and exclude == None:
            hashstr += str(key) + str(val)
    return hashstr

def present_scenario(val):
    from plotty.results.DataTypes import ScenarioValue
    if isinstance(val, ScenarioValue):
        if val.value != val.display:
            return '<span title="' + val.value + '">' + val.display + '</span>'
        else:
            return val.value
    return str(val)

def present_scenario_csv(val):
    from plotty.results.DataTypes import ScenarioValue
    if isinstance(val, ScenarioValue):
        return val.display
    return str(val)

def present_value(val):
    """ Turns a value into a state where it can be presented as HTML, including
        its confidence interval and sparkline if appropriate.
    """
    from plotty.results.DataTypes import DataAggregate  # Avoid a circular import issue in DataTypes
    if isinstance(val, DataAggregate):
        output = "%.3f" % val.value()
        ciDown, ciUp = val.ciPercent()
        if not math.isnan(ciUp):
            if ciDown == ciUp:
                output += ' <span class="ci">&plusmn;%.2f%%</span>' % ciDown
            else:
                output += ' <span class="ci">-%.2f%%, +%.2f%%</span>' % (ciDown, ciUp)
    else:
        output = str(val)
    return output
    
def present_value_csv(key, val, values_with_ci):
    """ Turns a value into a state where it can be presented in a CSV file,
        including its confidence interval if the column it appears in has
        confidence intervals somewhere in it.
    """
    from plotty.results.DataTypes import DataAggregate  # Avoid a circular import issue in DataTypes
    if key in values_with_ci:
        ciDown, ciUp = val.ci()
        if math.isnan(ciDown):
            return '%f,%f,%f' % (val.value(), val.value(), val.value())
        else:
            return '%f,%f,%f' % (val.value(), ciDown, ciUp)
    else:
        return str(val)

def present_value_csv_graph(val, useCI):
    """ Prints a value for CSV """
    from plotty.results.DataTypes import DataAggregate
    if useCI:
        if isinstance(val, DataAggregate):
            ciDown, ciUp = val.ci()
            if math.isnan(ciDown):
                return '%f,%f,%f' % (val.value(), val.value(), val.value())
            else:
                return '%f,%f,%f' % (val.value(), ciDown, ciUp)
        else:
            return '%f,%f,%f' % (val, val, val)
    else:
        return str(val)

def length_cmp(a, b):
    """ Used to sort a list of strings by their length in descending order """
    if len(a) == len(b):
        return 0
    elif len(a) < len(b):
        return 1
    else:
        return -1

def normdev(p):
    """ Compute negative Gaussian deviates
    
    Source: Michael J. Wichura. 1988. Algorithm AS 241: The Percentage Points of the Normal Distribution.
    Journal of the Royal Statistical Society. Series C (Applied Statistics), Vol. 37, No. 3, pp. 477-484
    http://www.jstor.org/stable/2347330 """

    a = [
        3.3871328727963666080e00,
        1.3314166789178437745e02,
        1.9715909503065514427e03,
        1.3731693765509461125e04,
        4.5921953931549871457e04,
        6.7265770927008700853e04,
        3.3430575583588128105e04,
        2.5090809287301226727e03,
    ]
    b = [
        0.0,  # unused
        4.2313330701600911252e01,
        6.8718700749205790830e02,
        5.3941960214247511077e03,
        2.1213794301586595867e04,
        3.9307895800092710610e04,
        2.8729085735721942674e04,
        5.2264952788528545610e03,
    ]
    c = [
        1.42343711074968357734e0,
        4.63033784615654529590e0,
        5.76949722146069140550e0,
        3.64784832476320460504e0,
        1.27045825245236838258e0,
        2.41780725177450611770e-1,
        2.27238449892691845833e-2,
        7.74545014278341407640e-4,
    ]
    d = [
        0.0,  # unused
        2.05319162663775882187e0,
        1.67638483018380384940e0,
        6.89767334985100004550e-1,
        1.48103976427480074590e-1,
        1.51986665636164571966e-2,
        5.47593808499534494600e-4,
        1.05075007164441684324e-9,
    ]
    e = [
        6.65790464350110377720e0,
        5.46378491116411436990e0,
        1.78482653991729133580e0,
        2.96560571828504891230e-1,
        2.65321895265761230930e-2,
        1.24266094738807843860e-3,
        2.71155556874348757815e-5,
        2.01033439929228813265e-7,
    ]
    f = [
        0.0,  # unused
        5.99832206555887937690e-1,
        1.36929880922735805310e-1,
        1.48753612908506148525e-2,
        7.86869131145613259100e-4,
        1.84631831751005468180e-5,
        1.42151175831644588870e-7,
        2.04426310338993978564e-15,
    ]

    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q*q
        ret = ((((((((a[7]*r + a[6])*r + a[5])*r + a[4])*r + a[3])*r + a[2])*r + a[1])*r + a[0]) /
               (((((((b[7]*r + b[6])*r + b[5])*r + b[4])*r + b[3])*r + b[2])*r + b[1])*r + 1.0))
        return ret
    else:
        if q < 0:
            r = p
        else:
            r = 1 - p
        if r <= 0:
            raise ArithmeticError("negative r")
        r = math.sqrt(-math.log(r))
        if r <= 5:
            r = r - 1.6
            ret = ((((((((c[7]*r + c[6])*r + c[5])*r + c[4])*r + c[3])*r + c[2])*r + c[1])*r + c[0]) /
                   (((((((d[7]*r + d[6])*r + d[5])*r + d[4])*r + d[3])*r + d[2])*r + d[1])*r + 1.0))
        else:
            r = r - 5
            ret = ((((((((e[7]*r + e[6])*r + e[5])*r + e[4])*r + e[3])*r + e[2])*r + e[1])*r + e[0]) /
                   (((((((f[7]*r + f[6])*r + f[5])*r + f[4])*r + f[3])*r + f[2])*r + f[1])*r + 1.0))
        if q < 0:
            ret = -ret
        return ret


def t_quantile(alpha, df):
    """ Compute the two-tailed t-dist quantile.
    two-tailed; so set alpha=0.05 to get 95% confidence
    
    Source: G. W. Hill. 1970. Algorithm 396: Students t-Quantiles. Commun. ACM 13, 10 (October 1970), 619-620.
    doi 10.1145/355598.355600 """
    if df < 1 or not (0 <= alpha < 1):
        return float('nan')

    if df == 2:
        return math.sqrt(2.0 / (alpha * (2.0 - alpha)) - 2.0)

    pi_2 = math.pi/2.0

    if df == 1:
        alpha *= pi_2
        return math.cos(alpha) / math.sin(alpha)

    a = 1.0 / (df - 0.5)
    b = 48.0 / (a ** 2)  # this line easy to transcribe wrong; this is the correct precedence
    c = ((20700*a/b - 98)*a - 16)*a + 96.36
    d = ((94.5/(b+c) - 3.0)/b + 1.0) * math.sqrt(a * pi_2) * df
    x = d * alpha
    y = math.pow(x, 2.0/df)
    if y > 0.05 + a:
        x = normdev(alpha * 0.5)
        y = x ** 2
        if df < 4:
            c = c + 0.3*(df - 4.5)*(x + 0.6)
        c = (((0.05*d*x - 5.0)*x - 7.0)*x - 2.0)*x + b + c
        y = (((((0.4*y + 6.3)*y + 36.0)*y + 94.5)/c - y - 3.0)/b + 1.0)*x
        y = a*(y ** 2)
        if y > 0.002:
            y = math.exp(y) - 1.0
        else:
            y = 0.5 * (y**2) + y
    else:
        y = ((1.0/(((df+6.0)/(df*y) - 0.089*d - 0.822)*(df + 2.0)*3.0) + 0.5/(df + 4.0))*y - 1.0) * (df+1.0)/(df+2.0) + 1.0/y

    return math.sqrt(df*y)

