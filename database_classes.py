import os
import sys
import json
import datetime
import uuid
import inspect
from copy import deepcopy
import treelib
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_KEYS_FILE = os.path.join(BASE_DIR, "database_keys.txt")
REQUIRED_PROPERTIES_FILE = os.path.join(BASE_DIR, "required_properties.txt")

SCHEMA_JSON_FILE = os.path.join(BASE_DIR, "schema.json")

def _migrate_to_json_if_needed():
    if not os.path.exists(SCHEMA_JSON_FILE):
        schema = {}
        if os.path.exists(REQUIRED_PROPERTIES_FILE):
            with open(REQUIRED_PROPERTIES_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or ":" not in line: continue
                    cls_name, props = line.split(":", 1)
                    cls_name = cls_name.strip()
                    keys = [k.strip() for k in props.split(",") if k.strip()]
                    if cls_name not in schema: schema[cls_name] = {"required": [], "custom": []}
                    schema[cls_name]["required"] = keys
        if os.path.exists(DATABASE_KEYS_FILE):
            with open(DATABASE_KEYS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or "_" not in line: continue
                    cls_name, prop = line.split("_", 1)
                    if cls_name not in schema: schema[cls_name] = {"required": [], "custom": []}
                    if prop not in schema[cls_name]["custom"] and prop not in schema[cls_name]["required"]:
                        schema[cls_name]["custom"].append(prop)
        if schema:
            with open(SCHEMA_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=4)
        else:
            with open(SCHEMA_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)

_migrate_to_json_if_needed()


class Sample:
    def __init__(self, required_properties=[], **kwargs):
        self.required_properties = required_properties

        # Check if all required properties are provided
        for prop in self.required_properties:
            if prop not in kwargs:
                raise ValueError(f"Missing required property for {self.__class__.__name__}: {prop}")
            
        # # Check if any kwargs look like typos of existing properties
        # with open(DATABASE_KEYS_FILE, 'a+') as f:
        #     f.seek(0)
        #     existing_keys = f.read().splitlines()
        #     type_prefix = self.type + '_'
        #     type_keys = [key[len(type_prefix):] for key in existing_keys if key.startswith(type_prefix)]
        #     for kwarg_key in kwargs.keys():
        #         # Check for possible typos: if the key is similar to an existing key for this type
        #         # For simplicity, warn if the key is not in type_keys and not in required_properties
        #         if kwarg_key not in type_keys and kwarg_key not in self.required_properties:
        #             print(f"Warning: '{kwarg_key}' is not a known property for {self.type}. Check for typos or add it intentionally.")

        # # Check if any of the kwargs are auto-generated properties and delete them if so
        # auto_props = ['id', 'entry_created_date']
        # for prop in auto_props:
        #     if prop in kwargs:
        #         print(f"Warning: {prop} will be auto-generated and should not be set manually. Deleting it from kwargs.")
        #         del kwargs[prop]
        

        # self.entry_created_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        # self.id = self.generate_id()
        # self.properties = kwargs  # Custom properties can be added as key=value pairs
        # self.log_keys()

        # Check if any kwargs look like typos of existing properties
        try:
            with open(SCHEMA_JSON_FILE, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            cls_schema = schema.get(self.__class__.__name__, {"required": [], "custom": []})
            type_keys = cls_schema["custom"] + cls_schema["required"]
            for kwarg_key in kwargs.keys():
                if kwarg_key == 'date': continue
                if kwarg_key not in type_keys and kwarg_key not in self.required_properties:
                    print(f"Warning: '{kwarg_key}' is not a known property for {self.__class__.__name__}. Check for typos or add it intentionally.")
        except Exception:
            pass

        # Check if any of the kwargs are auto-generated properties and delete them if so
        auto_props = ['id', 'entry_created_date']
        for prop in auto_props:
            if prop in kwargs:
                print(f"Warning: {prop} will be auto-generated and should not be set manually. Deleting it from kwargs.")
                del kwargs[prop]
        
        # Optional universal date property (keeps whatever user provided, or None)
        # It will also remain in self.properties if provided in kwargs
        self.date = kwargs.get('date', None)

        self.entry_created_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.id = self.generate_id()
        self.properties = kwargs  # Custom properties can be added as key=value pairs
        self.log_keys()

    @property
    def id(self):
        return self._id
    
    @property
    def entry_created_date(self):
        return self._entry_created_date

    def generate_id(self):
        # date_code = self.entry_created_date.strftime('%Y%m%d%H%M%S')
        unique_hex = uuid.uuid4().hex
        # Use at least 5 hex digits to make a collision among 1000 random codes very unlikely (less than 1% chance).
        # If you want extremely low risk (e.g. 1 in a billion), use 6 digits or more.
        return f"{unique_hex[:6]}"
    
    def add_property(self, key, value):
        """Add a custom property."""
        self.properties[key] = value

    def log_keys(self):
        """Add the keys to a global list"""
        try:
            with open(SCHEMA_JSON_FILE, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            cls_name = self.__class__.__name__
            if cls_name not in schema:
                schema[cls_name] = {"required": [], "custom": []}
            changed = False
            for key in self.properties.keys():
                if key not in schema[cls_name]["custom"] and key not in schema[cls_name]["required"] and key != 'date':
                    schema[cls_name]["custom"].append(key)
                    changed = True
            if changed:
                with open(SCHEMA_JSON_FILE, 'w', encoding='utf-8') as f:
                    json.dump(schema, f, indent=4)
        except Exception:
            pass

    def __setattr__(self, name, value):
        if name == 'id':
            if hasattr(self, '_id'):
                raise AttributeError("Sample ID cannot be changed once set.")
            self._id = value
        elif name == 'entry_created_date':
            if hasattr(self, '_entry_created_date'):
                raise AttributeError("Creation date cannot be changed once set.")
            self._entry_created_date = value
        else:
            self.__dict__[name] = value

    def __repr__(self):
        """ return a string that unambiguously describes the object"""
        return f"{self.__class__.__name__}(id={self.id}, created_date={self.entry_created_date}, properties={self.properties})"
    
    def add_property(self, key, value):
        """Add a custom property."""
        self.properties[key] = value


class Wafer(Sample):
    def __init__(self, **kwargs):
        required_properties = ['material',]
        super().__init__(required_properties, **kwargs)
        self.material = kwargs['material']
        self.permitted_children = ['Chip', 'SEM_stub', 'Annealing', 'XRay_analysis', 'Electrical_measurement', 'Micromechanical_testing', 'Swissmapper']
        # self.wafer_properties = kwargs  # Custom properties can be added as key=value pairs


class Chip(Sample):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)
        self.permitted_children = ['SEM_stub', 'Annealing', 'Chip', 'Imaging', 'XRay_analysis', 'Electrical_measurement', 'Micromechanical_testing', 'Swissmapper']


class SEM_stub(Sample):
    def __init__(self, **kwargs):
        required_properties = ['stub_diameter',]
        super().__init__(required_properties, **kwargs)
        self.stub_diameter = kwargs['stub_diameter']
        self.permitted_children = ['Pillar_array', 'Tensile_bar', 'TEM_lamella', 'Imaging', 'XRay_analysis', 'Micromechanical_testing', 'Swissmapper', 'Liftout', 'EBSD', 'FIB_milling']
        # self.stub_properties = kwargs  # Custom properties can be added as key=value pairs


class TEM_lamella(Sample):
    def __init__(self, **kwargs):
        required_properties = ['grid_material',]
        super().__init__(required_properties, **kwargs)
        self.grid_material = kwargs['grid_material']
        self.permitted_children = ['Liftout', 'Imaging', 'TKD', 'APT_tip', 'EBSD', 'Micromechanical_testing', 'FIB_milling',]


class Pillar_array(Sample):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)
        self.permitted_children = ['TEM_lamella', 'FIB_milling', 'Pillar_compression', 'Imaging', 'EBSD', 'Micromechanical_testing','Liftout',]


class Tensile_bar(Sample):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)
        self.permitted_children = ['TEM_lamella', 'FIB_milling', 'Imaging', 'TKD', 'EBSD', 'Micromechanical_testing','Liftout',]


class APT_tip(Sample):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)
        self.permitted_children = ['FIB_milling', 'Imaging',]




### Processing Steps ###

class Processing_Step(Sample):
    def __init__(self, required_properties=[], **kwargs):
        self.required_properties = required_properties
        self.permitted_children = []

        for prop in self.required_properties:
            if prop not in kwargs:
                raise ValueError(f"Missing required property for {self.__class__.__name__}: {prop}")

        try:
            with open(SCHEMA_JSON_FILE, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            cls_schema = schema.get(self.__class__.__name__, {"required": [], "custom": []})
            type_keys = cls_schema["custom"] + cls_schema["required"]
            for kwarg_key in kwargs.keys():
                if kwarg_key not in type_keys and kwarg_key not in self.required_properties:
                    print(f"Warning: '{kwarg_key}' is not a known property for {self.__class__.__name__}. Check for typos or add it intentionally.")
        except Exception:
            pass

        auto_props = ['id', 'entry_created_date']
        for prop in auto_props:
            if prop in kwargs:
                print(f"Warning: {prop} will be auto-generated and should not be set manually. Deleting it from kwargs.")
                del kwargs[prop]

        self.entry_created_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.id = self.generate_id()
        self.properties = kwargs
        self.log_keys()

    @property
    def id(self):
        return self._id

    @property
    def entry_created_date(self):
        return self._entry_created_date

    def generate_id(self):
        return f"P{uuid.uuid4().hex[:5]}"

    def add_property(self, key, value):
        self.properties[key] = value

    def log_keys(self):
        """Add the keys to a global list"""
        try:
            with open(SCHEMA_JSON_FILE, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            cls_name = self.__class__.__name__
            if cls_name not in schema:
                schema[cls_name] = {"required": [], "custom": []}
            changed = False
            for key in self.properties.keys():
                if key not in schema[cls_name]["custom"] and key not in schema[cls_name]["required"] and key != 'date':
                    schema[cls_name]["custom"].append(key)
                    changed = True
            if changed:
                with open(SCHEMA_JSON_FILE, 'w', encoding='utf-8') as f:
                    json.dump(schema, f, indent=4)
        except Exception:
            pass

    def __setattr__(self, name, value):
        if name == 'id':
            if hasattr(self, '_id'):
                raise AttributeError("Step ID cannot be changed once set.")
            self._id = value
        elif name == 'entry_created_date':
            if hasattr(self, '_entry_created_date'):
                raise AttributeError("Creation date cannot be changed once set.")
            self._entry_created_date = value
        else:
            self.__dict__[name] = value

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, created_date={self.entry_created_date}, properties={self.properties})"



class Annealing(Processing_Step):
    # Annealing step
    def __init__(self, **kwargs):
        required_properties = ['temperature_C', 'duration',]
        super().__init__(required_properties, **kwargs)
        self.permitted_children = ['Chip', 'SEM_stub']


class FIB_milling(Processing_Step):
    # Pillar milling step
    def __init__(self, **kwargs):
        required_properties = ['ion_species', 'microscope']
        super().__init__(required_properties, **kwargs)


class Liftout(Processing_Step):
    # Liftout step
    def __init__(self, **kwargs):
        required_properties = ['microscope', 'ion_species',]
        super().__init__(required_properties, **kwargs)
        self.permitted_children = ['TEM_lamella', 'APT_tip']


class Imaging(Processing_Step):
    def __init__(self, **kwargs):
        required_properties = ['microscope']
        super().__init__(required_properties, **kwargs)


class XRay_analysis(Processing_Step):
    def __init__(self, **kwargs):
        required_properties = ['mode',]
        super().__init__(required_properties, **kwargs)


class TKD(Processing_Step):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)


class EBSD(Processing_Step):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)


class Micromechanical_testing(Processing_Step):
    def __init__(self, **kwargs):
        required_properties = ['test_type',]
        super().__init__(required_properties, **kwargs)


class Electrical_measurement(Processing_Step):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)


class Swissmapper(Processing_Step):
    def __init__(self, **kwargs):
        required_properties = []
        super().__init__(required_properties, **kwargs)



def discover_required_properties():
    module = sys.modules[__name__]
    captured = {}
    orig_sample_init = Sample.__init__
    orig_proc_init = Processing_Step.__init__

    def _sample_wrapper(self, required_properties=[], **kwargs):
        captured[self.__class__.__name__] = list(required_properties)
        return None

    def _proc_wrapper(self, required_properties=[], **kwargs):
        captured[self.__class__.__name__] = list(required_properties)
        return None

    try:
        Sample.__init__ = _sample_wrapper
        Processing_Step.__init__ = _proc_wrapper
        classes = [obj for _, obj in inspect.getmembers(module, inspect.isclass)
                    if obj.__module__ == module.__name__]
        for cls in classes:
            try:
                cls()
            except Exception:
                pass
    finally:
        Sample.__init__ = orig_sample_init
        Processing_Step.__init__ = orig_proc_init

    result = {}
    for cls in classes:
        name = cls.__name__
        result[name] = captured.get(name, [])

    if os.path.exists(SCHEMA_JSON_FILE):
        with open(SCHEMA_JSON_FILE, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    else:
        schema = {}

    for name, props in result.items():
        if name not in schema:
            schema[name] = {"required": [], "custom": []}
        schema[name]["required"] = props

    with open(SCHEMA_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=4)

    return result

# Ignore the rest of the original function by finding where it ends (we just cut it out)
