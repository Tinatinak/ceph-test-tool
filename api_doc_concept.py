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

# TODO: Body parameters
# TODO: Make prettier! Namn, for-loopar, osv.

# TODO: (Make sure it works with other decorators (e.g. ApiController, Endpoint))
# TODO: Alphabethical?
# TODO: (Add more parameter types in later versions: [int], {[int]}, etc.)
# TODO: func = endpoint.func or make a property? Why doesn't endpoint.func.doc_info work?
# TODO: Make prettier!
# TODO: Learn how to use logger properly...git status
# TODO: Possibility to resuse parameters (e.g. fs_id) and resonses, using $ref?
#-----------------in __init__----------------------
def EndpointDoc(descr="", group="", param={}, body={}, respons={}):
    
    def _split(input):

        res = [] # In order to make it consistent with e.g. default params of today
        for key, value in input.items():
            if isinstance(value, tuple):
                res.append({
                    'name': key,
                    'type': value[0],
                    'description': value[1]
                })
            elif isinstance(value, dict):
                res.append({
                    'name': key,
                    'type': dict,
                    'properties': _split(value)
                })
            else: # CFor e.g. lists. Not yet implemented.
                res.append({
                    'name': key,
                    'type': object,
                    'unknown_props': value
                })
        return res # TODO: naming 

    for key, value in respons.items():
        respons[key] = _split(value)
        if isinstance(key, int):
            respons[str(key)] = respons.pop(key)

    def _wrapper(func):
        func.doc_info = {
            'summary': descr,
            'tag': group,
            'parameters': _split(param),
            'body': _split(body),
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
        }
    )
    def first_endpoint(self, my_num, my_string):
        print(my_string)
        return my_num   

class MySecondController():
    @EndpointDoc(
        descr = "This is a second dummy endpoint",
        respons = {
            200: {
                'name': (str, 'Description of name'),
                'age': (int, 'Description of age')
            },
        },
        body = {
            'user': {
                'username': {
                    'nickname': (str, 'desc'),
                    'realname': (str, 'desc')
                },
                'pass': (str, 'desc')
            },
            'colors': ["red, blue, yellow"]
        },
        group = "MyController"
    )
    def second_endpoint(self, user):
        print("2nd endpoint")
        return None

    def third_endpoint(self):
        print("3rd endpoint")
        return None


# This will be done automatically (and differently) in __init__
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
        """ Generates a list of all tags and corresponding descriptions. """
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
        """ Returns the name of a tag to assign to a path. """
        ctrl = endpoint.im_class
        tag = ctrl.__name__
        if hasattr(endpoint, 'doc_info') and endpoint.doc_info['tag']:
            tag = endpoint.doc_info['tag']
        elif hasattr(ctrl, 'doc_info') and ctrl.doc_info['tag']:
            tag = ctrl.doc_info['tag']
        return tag


    @classmethod
    # isinstance doesn't work: param_type is always a <type 'type'>. TODO: better with ==?
    def _type_to_str(cls, t): 
        if t is str:
            res = 'string'
        elif t is int:
            res = 'integer'
        elif t is bool:
            res = 'boolean'
        elif t is list:
            res = 'array'
        elif t is float:
            res = 'number'
        else:
            res = 'object'
        return res # TODO: naming


    @classmethod
    def _add_info_to_param(cls, parameter, p_info):
        for p in p_info:

            if p['name'] == parameter['name'] and 'description' in p:
                parameter['type'] = p['type']
                parameter['description'] = p['description']
            
            if 'properties' in p:
                parameter = cls._add_info_to_param(parameter, p['properties'])

            # if 'unknown_props' in p:
            #     pass
        return parameter # TODO: naming

    @classmethod
    def _gen_content(cls, input):
        properties = {}
        for item in input:
            properties[item['name']] = {
                'type': cls._type_to_str(item['type']),
                'description': item['description']
            }
            
        content = {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': properties   
                }
            }
        }
        return content
               
    @classmethod
    def _gen_responses(cls, method, return_objects={}):
        resp = {
            '400': {
                "description": "Operation exception. Please check the "
                               "response body for details."
            },
            '401': {
                "description": "Unauthenticated access. Please login first."
            },
            '403': {
                "description": "Unauthorized access. Please check your "
                               "permissions."
            },
            '500': {
                "description": "Unexpected error. Please check the "
                               "response body for the stack trace."
            }
        }
        if method.lower() == 'get':
            resp['200'] = {'description': "OK"}
        if method.lower() == 'post':
            resp['201'] = {'description': "Resource created."}
        if method.lower() == 'put':
            resp['200'] = {'description': "Resource updated."}
        if method.lower() == 'delete':
            resp['204'] = {'description': "Resource deleted."}
        if method.lower() in ['post', 'put', 'delete']:
            resp['202'] = {'description': "Operation is still executing."
                                          " Please check the task queue."}

        for code, content in return_objects.items(): # TODO: naming
            resp[code].update({'content': cls._gen_content(content)})

        return resp


    # Reduced version. Should include required or not
    # TODO: This assumes primitive types. Should/does it work for arrays?
    @classmethod
    def _gen_param(cls, param, location):
        parameters = {
            'name': param['name'],
            'in': location,
            'description': param['description'],
            'schema': {
                'type': cls._type_to_str(param['type'])
            }
        }
        return parameters

        
    # Reduced version. Should include all methods, security, body_params, etc.
    @classmethod
    def _gen_paths(cls):
        paths = {}

        for path, ep in sorted(list(ENDPOINT_MAP.items())):
            endpoint = ep[0]

            params = []
            if hasattr(endpoint, 'doc_info'):
                if endpoint.doc_info['summary']:
                    summary = endpoint.doc_info['summary']
                resp = endpoint.doc_info['respons']
                for param in endpoint.doc_info['parameters']: # TODO: naming
                    params.append(cls._gen_param(param, "query"))
            else: 
                summary = "No description available"
                resp = {} 

            methods = {
                'get': {
                    'tags': [cls._get_tag(endpoint)],
                    'summary': summary,
                    'responses': cls._gen_responses('get', resp),
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
