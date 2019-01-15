""" 
This file only intends to be used to try out solutions for generating documentation from code. 
To see resulting Swagger UI page, paste outcome from _gen_spec() in https://editor.swagger.io/ 
"""
import collections
import cherrypy
from distutils.util import strtobool

#-----------------in __init__----------------------
       
def ApiDoc(descr="(No description available)", tag=None, param=None, respons=None):
    # TODO: Allowed values for parameter type are: array, boolean, integer, number, object, string
    # I still haven't made it fit Open Api Spec for parameters of type dict (as for second_endpoint)
    def _gen_param_info(param_name, param_info):
        return {
            'param_name': param_name,
            'param_type': param_info[0],
            'param_descr': param_info[1],
        }
    parameters = []
    for param_name, param_info in param.items():
        if type(param_info) == dict:
            parameters.append({
                'param_name': param_name,
                'param_type': dict,
                'param_descr': "",
                'properties': [_gen_param_info(p_name, p_info) for p_name, p_info in param_info.items()]
            })
        else:
            parameters.append(_gen_param_info(param_name, param_info))
            
    def _wrapper(func):
        func._info_attr = {
            'summary': descr,
            'tag': tag,
            'parameters': parameters,
            'respons': respons
        }
        return func

    return _wrapper

class ClassApiDoc(object):
    def __init__(self, tag=None, descr=None):
        self.tag = tag
        self.tag_descr = descr
    
    def __call__(self, cls):
        cls._info_attr = {
            'tag': self.tag,
            'tag_descr': self.tag_descr
        }
        return cls

#-----------------at endpoints----------------------
@ClassApiDoc(descr = "This is a dummy controller")
class MyController():
    @ApiDoc(
        descr = "This is a dummy endpoint",
        param = {
            'my_num': (int, "A number of your choice"),
            'my_string': (str, "A dummy message") 
        },
        respons = {
            '200': "OK", # TODO: Make it possible to write respons code as int. Neccessary?
            '404': "Page not found"
        },
        )
    def first_endpoint(self, my_num, my_string):
        print(my_string)
        return my_num   

class MySecondController():
    @ApiDoc(
        descr = "This is a second dummy endpoint",
        param = {
            'user': {
                'username': (str, 'desc'),
                'pass': (str, 'desc')
            }
        },
        respons = {
            '401': "Not the default message" 
        },
        tag = "MyController"
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
class Docs():
    
    # Reduced version. Should check is_api, etc.
    # TODO: Assumptions correct? Add tests to verify?
    # Assuming tag names can only correspond to controller class names. 
    # Assuming tags can only be described once (at the class)
    @classmethod
    def _gen_tags(cls): 
        tags = []
        list_of_ctrl = set()

        for endpoints in ENDPOINT_MAP.values():
            for endpoint in endpoints:
                ctrl = endpoint.im_class
                list_of_ctrl.add(ctrl)
        
        for ctrl in sorted(list_of_ctrl):
            tag_name = ctrl.__name__
            tag_descr = "(No description available)"

            if hasattr(ctrl, '_info_attr'):
                if ctrl._info_attr['tag'] is not None:
                    tag_name = ctrl._info_attr['tag'] 
                if ctrl._info_attr['tag_descr'] is not None:
                    tag_descr = ctrl._info_attr['tag_descr'] 

            tags.append({
                'name': tag_name,
                'description': tag_descr
            })
    
        return tags

    @classmethod
    def _get_tag(cls, endpoint): 
        ctrl = endpoint.im_class
        if hasattr(endpoint, '_info_attr') and endpoint._info_attr['tag'] is not None:
            tag = endpoint._info_attr['tag']
        elif hasattr(ctrl, '_info_attr') and ctrl._info_attr['tag'] is not None:
            tag = ctrl._info_attr['tag']
        else: # Will be endpoint.group
            tag = ctrl.__name__
        return tag

    # Reduced version. Should include all default responses.
    @classmethod
    def _gen_responses_descr(cls, spec_respons=None):
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

    # Reduced version. Should include all allowed types.
    # allowedValues in Open API spec: array, boolean, integer, number, object, string
    @classmethod
    def _gen_type(cls, param):
        res = ""
        if param is str:
            res = "string"
        elif param is int:
            res = "integer"
        elif param is dict:
            return "object"  # dict not allowed
        return res

    # Reduced version. Should include required or not
    @classmethod
    def _gen_param(cls, param, location):
        parameters = {
            'name': param['param_name'],
            'in': location,
            'description': param['param_descr'],
            'schema': {
                'type': cls._gen_type(param['param_type'])
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
            params = [] # TODO: Make current values default. Add descr only if parameter exist. 
            if hasattr(endpoint, '_info_attr'):
                summary = endpoint._info_attr['summary']
                spec_resp = endpoint._info_attr['respons']
                for p in endpoint._info_attr['parameters']:
                    params.append(cls._gen_param(p, "query"))

            methods = {
                'get': {
                    'tags': [cls._get_tag(endpoint)],
                    'summary': summary,
                    'responses': cls._gen_responses_descr(spec_resp),
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

