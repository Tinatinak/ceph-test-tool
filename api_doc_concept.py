# Should both summary and description be included (for each path / method)? 
# Should responses be defined in ApiDocs?
# Should it be possible to document endpoints that not are api?
# Should I include ApiDoc-info in ENDPIOINT_MAP or in a seperate list/dict?
# Should the current info be overwritten directly or stored for other purposes?

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
        path = "/" + func.__name__ # Other solution needed for Ceph-code
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
        'my_num': ('integer', "A number of your choice"), # int or 'integer'? str or 'string'?
        'my_string': ('string', "A dummy message") 
    },
    respons = {
        '200': "OK", # Respons code as string or int?
        '404': "Page not found"
    },
    tag = "Group A"
    )
def first_endpoint(my_num, my_string):
    print(my_string)
    return my_num   

@ApiDoc(
    respons = {
        '401': "Not the default message" 
    },
    tag = "Group D"
    )
def second_endpoint():
    print("2nd endpoint")
    return None   


#-----------------in __docs.py__----------------------

# Should include ALL descriptions that should be available.
# (Manually defined since developers should be able to define their own group.)
API_TAGS = {
    'Group A': "A dummy description for Group A",
    'Group B': "This is the description of Group B",
    'Group C': "Group C is described here"
}

def _gen_tags():
    tags = []
    for tag in sorted(API_TAGS.keys()):
        tags.append({
            'name': tag, 
            'description': API_TAGS.get(tag)
        })
    return tags

# Reduced version. Should include all default responses.
def _gen_responses_descr(spec_respons=None):
    resp = {
        '400': {
            "description": "Operation exception. Please check the "
                           "response body for details."
        },
        '401': {
            "description": "Unauthenticated access. Please login first."
        },
        '500': {
            "description": "Unexpected error. Please check the "
                           "response body for the stack trace."
        }
    }
    if spec_respons is not None:
        for resp_code in spec_respons:
            resp[resp_code] = {"description": spec_respons.get(resp_code)}
    return resp

# Reduced version. Should include required or not
def _gen_param(param, location):
    parameters = {
        'name': param['param_name'],
        'in': location,
        'description': param['param_descr'],
        'schema': {
            'type': param['param_type']
        }
    }
    return parameters

      
# Reduced version. Should include all methods, security, body_params, etc.
def _gen_paths():

    paths = {}
    for endpoint in ENDPOINT_MAP:

        tag = ENDPOINT_MAP[endpoint][0]['tag']
        if tag is "":
            tag = "endpoint.method" # String for now since not defined for test-file
        if tag not in API_TAGS:
            API_TAGS[tag] = ""

        spec_resp = ENDPOINT_MAP[endpoint][0]['respons']

        # TODO: Make current values default. Add descr only if parameter exist. Both for query and path. 
        params = []
        for p in ENDPOINT_MAP[endpoint][0]['parameters'] :
            params.append(_gen_param(p, "query"))

        methods = {
            'get': {
                'tags': [tag],
                'summary': ENDPOINT_MAP[endpoint][0]['summary'],
                'responses': _gen_responses_descr(spec_resp),
                'parameters': params,
            }
        }        
        paths[endpoint] = methods

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
first_endpoint(42, "1st endpoint")
second_endpoint()
# print "------------------------------------"
# print _gen_tags()
# print "------------------------------------"
# print _gen_paths()
print "------------------------------------"
print _gen_spec()
