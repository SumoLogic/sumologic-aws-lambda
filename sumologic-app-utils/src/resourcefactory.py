from abc import ABCMeta

class ResourceFactory(object):
    resource_type = {}

    @classmethod
    def register(cls, objname, obj):
        print("registering", obj, objname)
        if objname not in ("SumoResource", "AWSResource"):
            cls.resource_type[objname] = obj

    @classmethod
    def get_resource(cls, objname):
        if objname in cls.resource_type:
            return cls.resource_type[objname]
        raise Exception("%s resource type is undefined" % objname)


class AutoRegisterResource(ABCMeta):
    def __new__(cls, clsname, bases, attrs):
        newclass = super(AutoRegisterResource, cls).__new__(cls, clsname, bases, attrs)
        ResourceFactory.register(clsname, newclass)
        return newclass

