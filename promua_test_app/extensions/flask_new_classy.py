#!/usr/bin/env python3

"""
    Flask-Classy
    ------------

    Class based views for the Flask microframework.

    :copyright: (c) 2014 by Freedom Dumlao.
    :license: BSD, see LICENSE for more details.

    /4kpt/
    Add:
        - hid static methods from routing;
        - add before function to use together with before_view_name;
        - add after function to use together with after_view_function.

"""

__version__ = "0.6.10"

import sys
import functools
import inspect
from collections import OrderedDict, ChainMap
from werkzeug.routing import parse_rule
from flask import request, Response, make_response
import re

_py2 = sys.version_info[0] == 2


def route(rule, **options):
    """A decorator that is used to define custom routes for methods in
    FlaskView subclasses. The format is exactly the same as Flask's
    `@app.route` decorator.
    """

    def decorator(f):
        # Put the rule cache on the method itself instead of globally
        if not hasattr(f, '_rule_cache') or f._rule_cache is None:
            f._rule_cache = {f.__name__: [(rule, options)]}
        elif not f.__name__ in f._rule_cache:
            f._rule_cache[f.__name__] = [(rule, options)]
        else:
            f._rule_cache[f.__name__].append((rule, options))

        return f

    return decorator


def before(*advance_function):
    """Wrapper uses to add same functionality to the different views.
       Adding a functions which run before wrapped function.

        :param advance_function:
            Iterated objects with adding functions.
            Alert !!!
                In flask_classy class this method must be a static
            Alert!!!

        Example:

        - decorate normal view function or decorate before_view function:

            class MyView(FlaskView):

                @staticmethod
                def call_first():
                    print "call first"

                @staticmethod
                def call_second():
                    print "call second"

                @before(call_first, call_second)
                def get():
                    print "call get"

            result: "call first", "call second", "call get"

    """

    def add_function(f):

        if not hasattr(f, '_rule_cache') or f._rule_cache is None:
            f._rule_cache = {"before_" + f.__name__: list(advance_function)}
        elif not "before_" + f.__name__ in f._rule_cache:
            f._rule_cache["before_" + f.__name__] = list(advance_function)
        else:
            f._rule_cache["before_" + f.__name__].extend(advance_function)

        return f

    return add_function


def after(*advance_function):

    """Wrapper uses to add same functionality to the different views.
       Adding a functions which run after wrapped function.

        :param advance_function:
            Iterated objects with adding functions.
            Alert !!! In flask_classy class this functions must be a static!!!

        Example:
        - decorate normal view function or decorate before_view function:

            class MyView(FlaskView):

                @staticmethod
                def call_first():
                    print "call first"

                @staticmethod
                def call_second():
                    print "call second"

                @after(call_first, call_second)
                def get():
                    print "call get"

            result: "call get", "call first", "call second"

    """

    def add_function(f):

        if not hasattr(f, '_rule_cache') or f._rule_cache is None:
            f._rule_cache = {"after_" + f.__name__: list(advance_function)}
        elif not "after_" + f.__name__ in f._rule_cache:
            f._rule_cache["after_" + f.__name__] = list(advance_function)
        else:
            f._rule_cache["after_" + f.__name__].extend(advance_function)

        return f

    return add_function


class FlaskView(object):
    """Base view for any class based views implemented with Flask-Classy. Will
    automatically configure routes when registered with a Flask app instance.
    """

    decorators = []
    route_base = None
    route_prefix = None
    trailing_slash = True

    @classmethod
    def register(cls, app, route_base=None, subdomain=None, route_prefix=None,
                 trailing_slash=None):
        """Registers a FlaskView class for use with a specific instance of a
        Flask app. Any methods not prefixes with an underscore are candidates
        to be routed and will have routes registered when this method is
        called.

        :param app: an instance of a Flask application

        :param route_base: The base path to use for all routes registered for
                           this class. Overrides the route_base attribute if
                           it has been set.

        :param subdomain:  A subdomain that this registration should use when
                           configuring routes.

        :param route_prefix: A prefix to be applied to all routes registered
                             for this class. Precedes route_base. Overrides
                             the class' route_prefix if it has been set.
        """

        if cls is FlaskView:
            raise TypeError("cls must be a subclass of FlaskView, not FlaskView itself")

        if route_base:
            cls.orig_route_base = cls.route_base
            cls.route_base = route_base

        if route_prefix:
            cls.orig_route_prefix = cls.route_prefix
            cls.route_prefix = route_prefix

        if not subdomain:
            if hasattr(app, "subdomain") and app.subdomain is not None:
                subdomain = app.subdomain
            elif hasattr(cls, "subdomain"):
                subdomain = cls.subdomain

        if trailing_slash is not None:
            cls.orig_trailing_slash = cls.trailing_slash
            cls.trailing_slash = trailing_slash


        members = get_interesting_members(FlaskView, cls)
        special_methods = ["get", "put", "patch", "post", "delete", "index"]

        for name, value in members:

            # create new before and after proxy
            special_proxy = None
            if hasattr(value, "_rule_cache"):
                special_proxy = cls.make_proxy_method(name, special_proxy=None,
                                                      **value._rule_cache)

            # create classic before, before_view, after and after_view
            proxy = cls.make_proxy_method(name, special_proxy=special_proxy)

            route_name = cls.build_route_name(name)
            try:

                if hasattr(value, "_rule_cache") and name in value._rule_cache:
                    for idx, cached_rule in enumerate(value._rule_cache[name]):
                        rule, options = cached_rule
                        rule = cls.build_rule(rule)
                        sub, ep, options = cls.parse_options(options)

                        if not subdomain and sub:
                            subdomain = sub

                        if ep:
                            endpoint = ep
                        elif len(value._rule_cache[name]) == 1:
                            endpoint = route_name
                        else:
                            endpoint = "%s_%d" % (route_name, idx)

                        app.add_url_rule(rule, endpoint, proxy,
                                         subdomain=subdomain, **options)

                elif name in special_methods:

                    if name in ["get", "index"]:
                        methods = ["GET"]
                    else:
                        methods = [name.upper()]

                    rule = cls.build_rule("/", value)
                    if not cls.trailing_slash:
                        rule = rule.rstrip("/")
                    app.add_url_rule(rule, route_name, proxy,
                                     methods=methods, subdomain=subdomain)

                else:
                    route_str = '/%s/' % name
                    if not cls.trailing_slash:
                        route_str = route_str.rstrip('/')
                    rule = cls.build_rule(route_str, value)
                    app.add_url_rule(rule, route_name,
                                     proxy, subdomain=subdomain)

            except DecoratorCompatibilityError:
                msg = "Incompatible decorator detected on {} in class {}"
                raise DecoratorCompatibilityError(msg.format(name,
                                                             cls.__name__))

        if hasattr(cls, "orig_route_base"):
            cls.route_base = cls.orig_route_base
            del cls.orig_route_base

        if hasattr(cls, "orig_route_prefix"):
            cls.route_prefix = cls.orig_route_prefix
            del cls.orig_route_prefix

        if hasattr(cls, "orig_trailing_slash"):
            cls.trailing_slash = cls.orig_trailing_slash
            del cls.orig_trailing_slash

    @classmethod
    def parse_options(cls, options):
        """Extracts subdomain and endpoint values from the options dict and
        returns them along with a new dict without those values.
        """
        options = options.copy()
        subdomain = options.pop('subdomain', None)
        endpoint = options.pop('endpoint', None)
        return subdomain, endpoint, options,

    @classmethod
    def make_proxy_method(cls, name, special_proxy=None, **proxy_functions):
        """Creates a proxy function that can be used by Flasks routing. The
        proxy instantiates the FlaskView subclass and calls the appropriate
        method.

        :param name: the name of the method to create a proxy for
        """

        i = cls()
        view = getattr(i, name)

        if cls.decorators:
            for decorator in cls.decorators:
                view = decorator(view)

        # active standard proxy
        if proxy_functions:

            @functools.wraps(view)
            def proxy(**forgettable_view_args):
                # Always use the global request object's view_args, because
                # they can be modified by intervening function before an
                # endpoint or wrapper gets called. This matches Flask's
                # behavior.
                del forgettable_view_args

                before_fullname = "before_{}".format(view.__name__)
                after_fullname = "after_{}".format(view.__name__)

                # before function
                if before_fullname in proxy_functions:
                    for func in proxy_functions[before_fullname]:
                        if isinstance(func, str):
                            # use string reference instead of function
                            func = (getattr(cls, func))
                        if hasattr(func, "__func__"):
                            # use staticmethod
                            response = func.__func__(**request.view_args)
                        else:
                            # use external function
                            response = func(**request.view_args)
                        # drop view from before function
                        if response:
                            return response

                # view function
                response = view(**request.view_args)
                if not isinstance(response, Response):
                    response = make_response(response)

                # after function
                if after_fullname in proxy_functions:
                    for func in proxy_functions[after_fullname]:
                        if isinstance(func, str):
                            # use string reference instead of function
                            func = (getattr(cls, func))
                        if hasattr(func, "__func__"):
                            # use staticmethod
                            response = func.__func__(response)
                        else:
                            # use external function
                            response = func(response)

                return response

            return proxy

        # active special before or after proxy
        else:

            @functools.wraps(view)
            def proxy(**forgettable_view_args):
                # Always use the global request object's view_args, because
                # they can be modified by intervening function before an
                # endpoint or wrapper gets called. This matches Flask's
                # behavior.
                del forgettable_view_args

                if hasattr(i, "before_request"):
                    response = i.before_request(name, **request.view_args)
                    if response is not None:
                        return response

                before_view_name = "before_" + name
                if hasattr(i, before_view_name):
                    before_view = getattr(i, before_view_name)
                    response = before_view(**request.view_args)
                    if response is not None:
                        return response

                if special_proxy:
                    response = special_proxy(**request.view_args)
                else:
                    response = view(**request.view_args)
                if not isinstance(response, Response):
                    response = make_response(response)

                after_view_name = "after_" + name
                if hasattr(i, after_view_name):
                    after_view = getattr(i, after_view_name)
                    response = after_view(response)

                if hasattr(i, "after_request"):
                    response = i.after_request(name, response)

                return response

            return proxy

    @classmethod
    def build_rule(cls, rule, method=None):
        """Creates a routing rule based on either the class name (minus the
        'View' suffix) or the defined `route_base` attribute of the class

        :param rule: the path portion that should be appended to the
                     route base

        :param method: if a method's arguments should be considered when
                       constructing the rule, provide a reference to the
                       method here. arguments named "self" will be ignored
        """

        rule_parts = []

        if cls.route_prefix:
            rule_parts.append(cls.route_prefix)

        route_base = cls.get_route_base()
        if route_base:
            rule_parts.append(route_base)

        rule_parts.append(rule)
        ignored_rule_args = ['self']
        if hasattr(cls, 'base_args'):
            ignored_rule_args += cls.base_args

        if method:
            args = get_true_argspec(method)[0]
            for arg in args:
                if arg not in ignored_rule_args:
                    rule_parts.append("<%s>" % arg)

        result = "/%s" % "/".join(rule_parts)
        return re.sub(r'(/)\1+', r'\1', result)

    @classmethod
    def get_route_base(cls):
        """Returns the route base to use for the current class."""

        if cls.route_base is not None:
            route_base = cls.route_base
            base_rule = parse_rule(route_base)
            cls.base_args = [r[2] for r in base_rule]
        else:
            if cls.__name__.endswith("View"):
                route_base = cls.__name__[:-4].lower()
            else:
                route_base = cls.__name__.lower()

        return route_base.strip("/")


    @classmethod
    def build_route_name(cls, method_name):
        """Creates a unique route name based on the combination of the class
        name with the method name.

        :param method_name: the method name to use when building a route name
        """
        return cls.__name__ + ":%s" % method_name


def get_interesting_members(base_class, cls):
    """Returns a list of methods that can be routed to"""

    base_members = dir(base_class)
    predicate = inspect.ismethod if _py2 else inspect.isfunction
    all_members = inspect.getmembers(cls, predicate=predicate)
    # my idea :)
    # all_members = (
    #    mbr for mbr in inspect.getmembers(cls, predicate=predicate)
    #    if _py2 or inspect.signature((mbr[1])).parameters.get("self")
    # )
    methods = ChainMap(*(super_class.__dict__ for super_class in cls.__mro__))
    return [member for member in all_members
            if not member[0] in base_members
            and ((hasattr(member[1], "__self__") and
                  not member[1].__self__ in inspect.getmro(cls))
                 if _py2 else
                 not isinstance(methods[member[0]], staticmethod))
            and not member[0].startswith("_")
            and not member[0].startswith("before_")
            and not member[0].startswith("after_")]


def get_true_argspec(method):
    """Drills through layers of decorators attempting to locate
    the actual argspec for the method.

    """

    argspec = inspect.getargspec(method)
    args = argspec[0]
    if args and args[0] == 'self':
        return argspec
    if hasattr(method, '__func__'):
        method = method.__func__
    if not hasattr(method, '__closure__') or method.__closure__ is None:
        raise DecoratorCompatibilityError

    closure = method.__closure__
    for cell in closure:
        inner_method = cell.cell_contents
        if inner_method is method:
            continue
        try:
            true_argspec = get_true_argspec(inner_method)
            if true_argspec:
                return true_argspec
        except TypeError:
            # not a callable cell
            continue


class DecoratorCompatibilityError(Exception):
    pass






