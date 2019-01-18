# -*- coding: utf-8 -*-
""" 
This file only intends to be used to try out solutions for generating documentation from code. 
To see resulting Swagger UI page, paste outcome from _gen_spec() in https://editor.swagger.io/ 
"""
""" NEWS:
Respons code as int (or str)
Changes in _gen_tags
Naming: EndpointDoc, GroupDoc, group instead of tag (only in decorator), _gen_responses
        type_to_string, doc_info (+ not private), 
"""
import collections
import cherrypy
from distutils.util import strtobool
import inspect

# TODO: Parameters should work for simple types (int, etc) and dict (see _gen_body_param)
# TODO: Add return-values (not the same as responses!)
# TODO: (Make sure it works with other decorators (e.g. ApiController, Endpoint))
# TODO: (Add more parameter types in later versions: [int], {[int]}, etc.)
#-----------------in __init__----------------------
       
def EndpointDoc(descr="", group="", param={}, respons={}):
    parameter_list = []
    for param_name, param_info in param.items():
        if isinstance(param_info, tuple):
            parameter_list.append({
                'param_name': param_name,
                'param_type': param_info[0],
                'param_descr': param_info[1],
            })
        else:
            parameter_list.append({
                'param_name': param_name,
                'param_type': None,
                'param_descr': "(No description available)",
                'properties': param_info
            })

    for key in respons.keys():
        if isinstance(key, int):
            respons[str(key)] = respons.pop(key)

    def _wrapper(func):
        func.doc_info = {
            'summary': descr,
            'tag': group,
            'parameters': parameter_list,
            'respons': respons
        }
        return func

    return _wrapper

class GroupDoc(object):
    def __init__(self, group="", descr=""):
        self.tag = group
        self.tag_descr = descr
    
    def __call__(self, cls):
        cls.doc_info = {
            'tag': self.tag,
            'tag_descr': self.tag_descr
        }
        return cls

#-----------------at endpoints----------------------
@GroupDoc(descr = "This is a dummy controller")
class MyController():
    @EndpointDoc(
        descr = "This is a dummy endpoint",
        param = {
            'my_num': (int, "A number of your choice"),
            'my_string': (str, "A dummy message") 
        },
        respons = {
            200: "OK",
            '404': "Page not found"
        }
    )
    def first_endpoint(self, my_num, my_string):
        print(my_string)
        return my_num   

class MySecondController():
    @EndpointDoc(
        descr = "This is a second dummy endpoint",
        respons = {
            401: "Not the default message" 
        },
        param = {
            'user': {
                'username': (str, 'desc'),
                'pass': (str, 'desc')
            }
        },
        group = "MyController"
    )
    def second_endpoint(self, user):
        print("2nd endpoint")
        return None

    def third_endpoint(self):
        print("3rd endpoint")
        return None


# TODO: This will be done automatically (and differently) in __init__
ctrl_class = MyController()
first_endpoint = ctrl_class.first_endpoint

ctrl_class = MySecondController()
second_endpoint = ctrl_class.second_endpoint
third_endpoint = ctrl_class.third_endpoint

ENDPOINT_MAP = collections.defaultdict(list)

ENDPOINT_MAP["/" + first_endpoint.__name__].append(first_endpoint)
ENDPOINT_MAP["/" + second_endpoint.__name__].append(second_endpoint)
ENDPOINT_MAP["/" + third_endpoint.__name__].append(third_endpoint)


#-----------------in docs.py----------------------
@EndpointDoc()
class Docs():

    # Reduced version. Should check is_api, etc.
    @classmethod
    def _gen_tags(cls):
        """ To generate a list of all tags in form [{name: description}] """
        list_of_ctrl = set()
        for endpoints in ENDPOINT_MAP.values():
            for endpoint in endpoints:
                ctrl = endpoint.im_class
                list_of_ctrl.add(ctrl)

        tags = []        
        for ctrl in list_of_ctrl:
            tag_name = ctrl.__name__
            tag_descr = "*No description available*"

            if hasattr(ctrl, 'doc_info'):
                if ctrl.doc_info['tag']:
                    tag_name = ctrl.doc_info['tag'] 
                if ctrl.doc_info['tag_descr']:
                    tag_descr = ctrl.doc_info['tag_descr'] 
            tags.append({
                'name': tag_name,
                'description': tag_descr
            })
        tags.sort(key=lambda e : e['name'])
        return tags

    @classmethod
    def _get_tag(cls, endpoint): 
        """ Returns the name of a tag to assign to a path """
        ctrl = endpoint.im_class
        tag = ctrl.__name__
        if hasattr(endpoint, 'doc_info') and endpoint.doc_info['tag']:
            tag = endpoint.doc_info['tag']
        elif hasattr(ctrl, 'doc_info') and ctrl.doc_info['tag']:
            tag = ctrl.doc_info['tag']
        return tag

    # Reduced version. Should include all default responses.
    @classmethod
    def _gen_responses(cls, spec_resp={}):
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

        for resp_code in spec_resp:
            resp[resp_code] = {"description": spec_resp[resp_code]}
        return resp

    @classmethod
    def _type_to_str(cls, param_type):
        if isinstance(param_type, str):
            res = 'string'
        elif isinstance(param_type, int):
            res = 'integer'
        elif isinstance(param_type, bool):
            res = 'boolean'
        elif isinstance(param_type, list):
            res = 'array'
        elif isinstance(param_type, float):
            res = 'number'
        else:
            res = 'object'
        return res

    # Reduced version. Should include required or not
    @classmethod
    def _gen_param(cls, param, location):
        parameters = {
            'name': param['param_name'],
            'in': location,
            'description': param['param_descr'],
            'schema': {
                'type': cls._type_to_str(param['param_type'])
            }
        }
        if param.has_key('properties'):
            pass
            #TODO: Make this fit Open Api Spec
        return parameters

        
    # Reduced version. Should include all methods, security, body_params, etc.
    @classmethod
    def _gen_paths(cls):
        paths = {}

        for path, ep in sorted(list(ENDPOINT_MAP.items())):
            endpoint = ep[0]
            
            summary = "(No description available)"
            params = []
            if hasattr(endpoint, 'doc_info'):
                if endpoint.doc_info['summary']:
                    summary = endpoint.doc_info['summary']
                spec_resp = endpoint.doc_info['respons']
                for p in endpoint.doc_info['parameters']:
                    params.append(cls._gen_param(p, "query"))

            methods = {
                'get': {
                    'tags': [cls._get_tag(endpoint)],
                    'summary': summary,
                    'responses': cls._gen_responses(spec_resp),
                    'parameters': params,
                }
            }        
            paths[path] = methods

        return paths


    # Reduced version. Included only for demonstrational purpose.
    def _gen_spec(self, all_endpoints=False, baseUrl=""):
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
            'tags': self._gen_tags(),
            'schemes': [scheme],
            'paths': self._gen_paths(),
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
print Docs()._gen_spec()
#Docs()._gen_spec()
