# Should both summary and description be included (for each path / method)? 
# Should responses be defined in ApiDocs?
# Should it be possible to document endpoints that not are api?
# How do I include ApiDoc-info in ENDPIOINT_MAP in real varsion? How much is still needed?

import collections
import cherrypy
from distutils.util import strtobool


#-----------------in __init__----------------------
ENDPOINT_MAP = collections.defaultdict(list)

def ApiDoc(descr="", tag="", param=None, respons=None):

    parameters = []
    if param is not None: 
        for p in param:
            parameters.append ({
                'param_name': p,
                'param_type': param[p][0],
                'param_descr': param[p][1]
            })

    def _wrapper(func):
        path = "/" + func.__name__
        ENDPOINT_MAP[path].append({
            'summary': descr,
            'tag': tag,
            'parameters': parameters,
            'respons': respons
        })
        return func

    return _wrapper


#-----------------at endpoint----------------------
@ApiDoc(
    descr = "A dummy endpoint",
    param = {
        'my_num': (int, "A number of your choice"),
        'my_string': (str, "A dummy message")
    },
    respons = {
        200: "OK", 
        404: "Page not found"
    },
    tag = "Group A"
    )
def test_endpoint(my_num, my_string):
    print(my_string)
    return my_num   


#-----------------in __docs.py__----------------------

# To include all descriptions that should be available.
# (Manually defined since group should be defined by the developers.)
API_TAGS = {
    'Group A': "A dummy description for Group A",
    'Group B': "This is the description of Group B",
    'Group C': "Group C is descibed here"
}

# Reduced version. Should control if is_api, etc.
# Should return current values if tag="".
def _gen_tags():
    tags = []
    for endpoint in ENDPOINT_MAP:
        tag = ENDPOINT_MAP[endpoint][0]['tag']
        if tag in API_TAGS.keys():
            tags.append({
                'name': tag,
                'description': API_TAGS.get(tag)
            })

    return tags

# Reduced version. Should include Parameter location, etc.
def _gen_param(param):
    parameters = {
        'name': param['param_name'],
        'description': param['param_descr'],
        'schema': { # Is it necessary to have 'schema'?
            'type': param['param_type']
        }
    }
    return parameters
        
# Reduced version. Should include all methods, security, etc. . 
# Should return current values if None.
def _gen_paths():

    paths = {}
    for path in ENDPOINT_MAP:
        params = []
        for p in ENDPOINT_MAP[path][0]['parameters'] :
            params.append(_gen_param(p))

        methods = {
            'get': {
                'tags': [ENDPOINT_MAP[path][0]['tag']],
                'summary': ENDPOINT_MAP[path][0]['summary'],
                'responses': ENDPOINT_MAP[path][0]['respons'], # Not correct format yet.
                'parameters': params,
            }
        }        
        paths[path] = methods

    return paths

# Reduced version. Included only for demonstrational purpose.
def _gen_spec(all_endpoints=False, baseUrl=""):
    if all_endpoints:
        baseUrl = ""
    if not baseUrl:
        baseUrl = "/"

    scheme = 'https'
    # ssl = strtobool(mgr.get_localized_module_option('ssl', 'True'))
    # if not ssl:
    #     scheme = 'http'
    host = cherrypy.request.base
    # host = host[host.index(':')+3:]

    spec = {
        'openapi': "3.0.0",
        'info': {
            'description': "Please note that this API is not an official "
                           "Ceph REST API to be used by third-party "
                           "applications. It's primary purpose is to serve"
                           " the requirements of the Ceph Dashboard and is"
                           " subject to change at any time. Use at your "
                           "own risk.",
            'version': "v1",
            'title': "Ceph-Dashboard REST API"
        },
        'host': host,
        'basePath': baseUrl,
        'servers': [{'url': "{}{}".format(cherrypy.request.base, baseUrl)}],
        'tags': _gen_tags(),
        'schemes': [scheme],
        'paths': _gen_paths(),
        'components': {
            'securitySchemes': {
                'jwt': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT'
                }
            }
        }
    }

    return spec



#-----------------To test/demonstrate----------------------
print test_endpoint(42, "Hi!")
print "------------------------------------"
print _gen_tags()
print "------------------------------------"
print _gen_paths()
print "------------------------------------"
print _gen_spec()
