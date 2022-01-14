import os
import pymysql
from flask import Flask, render_template, url_for, jsonify
from cachelib.simple import SimpleCache

# average build time per package/arch

CACHE_TIMEOUT = 60 * 60 # hour

app = Flask(__name__)
cache = SimpleCache()

DB_HOST = os.environ.get('DB_HOST', '0.0.0.0')
DB_PORT = int(os.environ.get('DB_PORT', 3306))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'my-secret-pw')
DB_NAME = 'koji'


def get_cursor():
    # TODO: opening connections but not closing
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD)
    return conn.cursor()


def get_methods():
    key = 'methods'
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        c.execute("SELECT DISTINCT method FROM task ORDER BY method")
        data = [x[0] for x in c.fetchall()]
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return data


def get_channels(name_only=True, id_map=False):
    key = 'channels'
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        c.execute("SELECT id, name FROM channels ORDER BY name")
        data = {}
        for id, name in c.fetchall():
            data[name] = id
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    if id_map:
        m = {}
        for name, id in data.items():
            m[id] = name
        return m
    elif name_only:
        return sorted(data.keys())
    else:
        return data


def get_packages():
    key = 'packages'
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        c.execute("SELECT name FROM package ORDER BY name")
        data = [x[0] for x in c.fetchall()]
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return data


def get_users():
    key = 'users'
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        c.execute("SELECT id, name FROM users ORDER BY name")
        data = [{'id': x[0], 'name': x[1]} for x in c.fetchall()]
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return data


def get_user_id(username):
    users = get_users()
    for u in users:
        if u['name'] == username:
            return u['id']
    raise ValueError("User %s not found" % username)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/charts/method/<method>/<scope>/<counts>')
def method(method, scope, counts):
    return render_template(
        'method.html',
        method=method,
        scope=scope,
        methods=get_methods(),
        counts=counts
    )


@app.route('/charts/methods/<scope>/<counts>')
def methods(scope, counts):
    return render_template(
        'methods.html',
        scope=scope,
        counts=counts,
    )


@app.route('/charts/channel/<channel>/<scope>/<counts>')
def channel(channel, scope, counts):
    return render_template(
        'channel.html',
        channel=channel,
        scope=scope,
        channels=get_channels(),
        counts=counts,
    )


@app.route('/charts/channels/<scope>/<counts>')
def channels(scope, counts):
    return render_template(
        'channels.html',
        scope=scope,
        counts=counts,
    )


@app.route('/charts/users/<path:user>/<method>/<scope>/<counts>')
def user_method(user, method, scope, counts):
    return render_template(
        'user_method.html',
        user=user,
        method=method,
        scope=scope,
        users=get_users(),
        methods=get_methods(),
        counts=counts
    )

@app.route('/charts/package/<package>/<scope>/<counts>')
def package(package, scope, counts):
    return render_template(
        'package.html',
        packages=get_packages(),
        package=package,
        scope=scope,
        counts=counts
    )


def get_grouping(scope, agg):
    if scope == 'all':
        group_by = "%Y-%m"
        interval = "50 YEAR"
    elif scope == '3-years':
        group_by = "%Y-%m-%d"
        interval = "3 YEAR"
    elif scope == 'year':
        group_by = "%Y-%m-%d"
        interval = "1 YEAR"
    elif scope == '6-months':
        group_by = "%Y-%m-%d"
        interval = "6 MONTH"
    elif scope == '3-months':
        group_by = "%Y-%m-%d"
        interval = "3 MONTH"
    elif scope == 'month':
        group_by = "%Y-%m-%d"
        interval = "1 MONTH"
    elif scope == 'week':
        group_by = "%Y-%m-%d"
        interval = "1 WEEK"
    elif scope == 'day':
        group_by ="%Y-%m-%d %H:00"
        interval = "1 DAY"
    elif scope == 'hour':
        group_by = "%Y-%m-%d %H:%i"
        interval = "1 HOUR"
    else:
        raise ValueError("Wrong scope: %s" % scope)

    if agg == 'counts':
        selector = "COUNT(*)"
        where = 'TRUE'
        ytitle = 'Number of tasks'
    elif agg == 'times':
        selector = "CAST(TIME_TO_SEC(TIMEDIFF(completion_time, create_time)) / 60 AS INTEGER)"
        where = 'completion_time != ""'
        ytitle = 'Time in minutes'
    elif agg == 'averages':
        #selector = "AVG(completion_time - create_time)"
        selector = "CAST(AVG(TIMEDIFF(completion_time, create_time)) / 60 AS INTEGER)"
        where = 'completion_time != ""'
        ytitle = 'Average time in minutes'
    elif agg == 'medians':
        selector = "CAST(MEDIAN(TIMEDIFF(completion_time, create_time)) OVER (PARTITION BY day, method) / 60 AS INTEGER)"
        where = 'completion_time != ""'
        ytitle = 'Median time in minutes'
    elif agg == 'waits':
        selector = "CAST(TIME_TO_SEC(TIMEDIFF(start_time, create_time)) / 60 AS INTEGER)"
        where = 'start_time != ""'
        ytitle = 'Waiting time in minutes'
    else:
        raise ValueError("Wrong aggregate: %s" % agg)

    return group_by, interval, selector, where, ytitle


@app.route("/data/method/<method>/<scope>/<counts>")
def data_method(method, scope, counts):
    key = 'method-%s-%s-%s' % (method, scope, counts)
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        group_by, interval, selector, where, ytitle = get_grouping(scope, counts)
        group_by = group_by.replace('%', '%%')
        interval = interval.replace('%', '%%')

        q = """
        SELECT %s, DATE_FORMAT(create_time, "%s") AS day
        FROM task
        WHERE
            create_time > DATE_SUB(NOW(), INTERVAL %s) AND
            method = %%s
            AND %s
        GROUP BY day
        ORDER BY day
        """ % (selector, group_by, interval, where)
        c.execute(q, (method,))
        data = {
            'data': [],
            'title': '%s tasks last %s' % (method, scope),
            'ytitle': ytitle,
        }
        for count, date in c.fetchall():
            try:
                count = int(count)
            except:
                count = 0
            data['data'].append({'x': date, 'y': count})
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return jsonify(data)


@app.route("/data/methods/<scope>/<counts>")
def data_methods(scope, counts):
    key = 'methods-%s-%s' % (scope, counts)
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        group_by, interval, selector, where, ytitle = get_grouping(scope, counts)

        q = """
        SELECT %s, method, DATE_FORMAT(create_time, "%s") AS day
        FROM task
        WHERE
            create_time > DATE_SUB(NOW(), INTERVAL %s)
            AND %s
        GROUP BY day, method
        ORDER BY day
        """ % (selector, group_by, interval, where)
        c.execute(q)

        data = {}
        keys = set()
        for count, method, date in c.fetchall():
            data.setdefault(method, {})
            data[method][date] = count
            keys.add(date)
        tmp = {}
        keys = sorted(keys)
        for method in data:
            l = []
            for key in keys:
                l.append({
                    'x': key,
                    'y': data[method].get(key, 0)
                })
            tmp[method] = l
        data = {
            'data': tmp,
            'title': 'All tasks last %s' % scope,
            'xtitle': 'Date',
            'ytitle': ytitle,
        }
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return jsonify(data)


@app.route("/data/channel/<channel>/<scope>/<counts>")
def data_channel(channel, scope, counts):
    key = 'channel-%s-%s-%s' % (channel, scope, counts)
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        group_by, interval, selector, where, ytitle = get_grouping(scope, counts)
        channel_id = get_channels(name_only=False)[channel]

        q = """
        SELECT %s, DATE_FORMAT(create_time, "%s") AS day
        FROM task
        WHERE
            task.channel_id = %s
            AND create_time > DATE_SUB(NOW(), INTERVAL %s)
            AND %s
        GROUP BY day
        ORDER BY day
        """ % (selector, group_by, channel_id, interval, where)
        c.execute(q)
        data = {
            'data': [],
            'title': '%s tasks last %s' % (channel, scope),
            'ytitle': ytitle,
        }
        for count, date in c.fetchall():
            try:
                count = int(count)
            except:
                count = 0
            data['data'].append({'x': date, 'y': count})
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return jsonify(data)


@app.route("/data/channels/<scope>/<counts>")
def data_channels(scope, counts):
    key = 'channels-%s-%s' % (scope, counts)
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        group_by, interval, selector, where, ytitle = get_grouping(scope, counts)

        q = """
        SELECT %s, channel_id, DATE_FORMAT(create_time, "%s") AS day
        FROM task
        WHERE
            create_time > DATE_SUB(NOW(), INTERVAL %s)
            AND %s
        GROUP BY day, channel_id
        ORDER BY day
        """ % (selector, group_by, interval, where)
        c.execute(q)

        channels = get_channels(id_map=True)
        data = {}
        keys = set()
        for count, channel_id, date in c.fetchall():
            channel = channels[channel_id]
            data.setdefault(channel, {})
            data[channel][date] = count
            keys.add(date)
        tmp = {}
        keys = sorted(keys)
        for channel in data:
            l = []
            for key in keys:
                l.append({
                    'x': key,
                    'y': data[channel].get(key, 0),
                })
            tmp[channel] = l
        data = {
            'data': tmp,
            'title': 'All tasks last %s' % scope,
            'xtitle': 'Date',
            'ytitle': ytitle,
        }
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return jsonify(data)


@app.route("/data/users/<path:user>/<method>/<scope>/<counts>")
def data_user_method(user, method, scope, counts):
    key = 'usermethod-%s-%s-%s-%s' % (user, method, scope, counts)
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        group_by, interval, selector, where, ytitle = get_grouping(scope, counts)
        q = """
        SELECT %(selector)s, DATE_FORMAT(create_time, "%(group_by)s") AS day
        FROM task
        WHERE
            create_time > DATE_SUB(NOW(), INTERVAL %(interval)s) AND
            owner = %(owner)i AND
            method = "%(method)s" AND
            %(where)s
        GROUP BY day
        ORDER BY day
        """ % {
            'selector': selector,
            'group_by': group_by,
            'owner': get_user_id(user),
            'interval': interval,
            'method': method,
            'where': where,
        }
        c.execute(q)
        data = {
            'data': [],
            'title': '%s tasks last %s' % (method, scope),
            'ytitle': ytitle,
        }
        for count, date in c.fetchall():
            try:
                count = int(count)
            except:
                count = 0
            data['data'].append({'x': date, 'y': count})
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return jsonify(data)


@app.route("/data/package/<package>/<scope>/<counts>")
def data_package(package, scope, counts):
    key = 'package-%s-%s-%s' % (package, scope, counts)
    data = cache.get(key)
    if data is None:
        c = get_cursor()
        group_by, interval, selector, where, ytitle = get_grouping(scope, counts)

        q = "SELECT id FROM package WHERE name = %s"
        c.execute(q, package)
        pkg_id = c.fetchall()[0][0]

        q = """
        SELECT %s, DATE_FORMAT(start_time, "%s") AS day
        FROM build
        WHERE
            start_time > DATE_SUB(NOW(), INTERVAL %s) AND
            pkg_id = %s
            AND %s
        GROUP BY day
        ORDER BY day
        """ % (selector, group_by, interval, pkg_id, where)
        c.execute(q)
        data = {
            'data': [],
            'title': '%s tasks last %s' % (method, scope),
            'ytitle': ytitle,
        }
        for count, date in c.fetchall():
            try:
                count = int(count)
            except:
                count = 0
            data['data'].append({'x': date, 'y': count})
        cache.set(key, data, timeout=CACHE_TIMEOUT)
    return jsonify(data)
