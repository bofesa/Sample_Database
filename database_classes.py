import os
import sys
import json
import datetime
import inspect
from copy import deepcopy
import treelib
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import shutil
from database_lock import DatabaseFileLock, atomic_write_json
from id_policy import DEFAULT_ID_TOTAL_LENGTH, generate_random_id, validate_id_total_length

if getattr(sys, "frozen", False):
    # running as exe (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # running as .py script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_KEYS_FILE = os.path.join(BASE_DIR, "database_keys.txt")
REQUIRED_PROPERTIES_FILE = os.path.join(BASE_DIR, "required_properties.txt")
DATABASE_STRUCTURE_FILE = os.path.join(BASE_DIR, "database_structure.json")
SCHEMA_SETTINGS_KEY = "__settings__"


def load_database_structure():
    if not os.path.exists(DATABASE_STRUCTURE_FILE):
        default = globals().get("DEFAULT_SCHEMA", {})
        return deepcopy(default)
    with open(DATABASE_STRUCTURE_FILE, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("database_structure.json must contain a JSON object.")
    return data


def schema_class_items(schema):
    return [
        (name, config)
        for name, config in schema.items()
        if name != SCHEMA_SETTINGS_KEY and isinstance(config, dict)
    ]


def schema_class_names(schema):
    return [name for name, _config in schema_class_items(schema)]


def update_database_structure(mutator):
    """Apply one locked read-modify-write transaction to the structure file."""
    structure_lock = DatabaseFileLock(DATABASE_STRUCTURE_FILE)
    if not structure_lock.acquire():
        raise RuntimeError(structure_lock.reason or "database_structure.json is locked.")
    try:
        schema = load_database_structure()
        original = deepcopy(schema)
        result = mutator(schema)
        if schema != original or not os.path.exists(DATABASE_STRUCTURE_FILE):
            atomic_write_json(DATABASE_STRUCTURE_FILE, schema, indent=4)
        return result
    finally:
        structure_lock.release()


def get_id_total_length():
    schema = load_database_structure()
    settings = schema.get(SCHEMA_SETTINGS_KEY, {})
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError(f"{SCHEMA_SETTINGS_KEY} must be a JSON object.")
    return validate_id_total_length(settings.get("id_total_length", DEFAULT_ID_TOTAL_LENGTH))


def set_id_total_length(value):
    new_length = validate_id_total_length(value)

    def apply(schema):
        settings = schema.setdefault(SCHEMA_SETTINGS_KEY, {})
        if not isinstance(settings, dict):
            raise ValueError(f"{SCHEMA_SETTINGS_KEY} must be a JSON object.")
        current = validate_id_total_length(
            settings.get("id_total_length", DEFAULT_ID_TOTAL_LENGTH)
        )
        if new_length < current:
            raise ValueError(f"ID length cannot be reduced from {current} to {new_length}.")
        settings["id_total_length"] = new_length
        return new_length

    return update_database_structure(apply)


class Sample:
    def __init__(self, required_properties=[], **kwargs):
        generated_id = kwargs.pop("_generated_id", None)
        self.required_properties = required_properties

        # Check if all required properties are provided
        for prop in self.required_properties:
            if prop not in kwargs:
                raise ValueError(f"Missing required property for {self.__class__.__name__}: {prop}")

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
            with open(DATABASE_STRUCTURE_FILE, 'r', encoding='utf-8') as f:
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
        self.id = generated_id if generated_id is not None else self.generate_id()
        self.properties = kwargs  # Custom properties can be added as key=value pairs
        self.log_keys()

    @property
    def id(self):
        return self._id
    
    @property
    def entry_created_date(self):
        return self._entry_created_date

    def generate_id(self):
        return generate_random_id(DEFAULT_ID_TOTAL_LENGTH, processing_step=False)
    
    def add_property(self, key, value):
        """Add a custom property."""
        self.properties[key] = value

    def log_keys(self):
        """Add the keys to a global list"""
        try:
            cls_name = self.__class__.__name__
            def apply(schema):
                if cls_name not in schema:
                    schema[cls_name] = {"required": [], "custom": []}
                for key in self.properties.keys():
                    if key not in schema[cls_name]["custom"] and key not in schema[cls_name]["required"] and key != 'date':
                        schema[cls_name]["custom"].append(key)
            update_database_structure(apply)
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
    
    def clone(self, _generated_id=None, **overrides):
        """
        Return a new instance of the same class, copying the properties.
        Overrides can be provided to modify properties during the clone.
        """
        new_props = deepcopy(self.properties)
        new_props.update(overrides)
        old_date = getattr(self, 'date', None)
        if old_date is not None and 'date' not in overrides:
            new_props['date'] = old_date
        if _generated_id is not None:
            new_props["_generated_id"] = _generated_id
        return self.__class__(**new_props)







### Processing Steps ###

class Processing_Step(Sample):
    def __init__(self, required_properties=[], **kwargs):
        generated_id = kwargs.pop("_generated_id", None)
        self.required_properties = required_properties
        self.permitted_children = []

        for prop in self.required_properties:
            if prop not in kwargs:
                raise ValueError(f"Missing required property for {self.__class__.__name__}: {prop}")

        try:
            with open(DATABASE_STRUCTURE_FILE, 'r', encoding='utf-8') as f:
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
        self.id = generated_id if generated_id is not None else self.generate_id()
        self.properties = kwargs
        self.log_keys()

    @property
    def id(self):
        return self._id

    @property
    def entry_created_date(self):
        return self._entry_created_date

    def generate_id(self):
        return generate_random_id(DEFAULT_ID_TOTAL_LENGTH, processing_step=True)

    def add_property(self, key, value):
        self.properties[key] = value

    def log_keys(self):
        """Add the keys to a global list"""
        try:
            cls_name = self.__class__.__name__
            def apply(schema):
                if cls_name not in schema:
                    schema[cls_name] = {"required": [], "custom": []}
                for key in self.properties.keys():
                    if key not in schema[cls_name]["custom"] and key not in schema[cls_name]["required"] and key != 'date':
                        schema[cls_name]["custom"].append(key)
            update_database_structure(apply)
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


DEFAULT_SCHEMA = {
    SCHEMA_SETTINGS_KEY: {
        "id_total_length": DEFAULT_ID_TOTAL_LENGTH
    },
    "Sample": {
        "base": None,
        "required": [],
        "custom": [],
        "permitted_children": []
    },
    "Processing_Step": {
        "base": "Sample",
        "required": [],
        "custom": [],
        "permitted_children": []
    },
    "Wafer": {
        "base": "Sample",
        "required": [
            "material"
        ],
        "custom": [],
        "permitted_children": [
            "Chip",
            "SEM_stub",
            "Annealing",
            "XRay_analysis",
            "Electrical_measurement",
            "Micromechanical_testing",
            "Swissmapper"
        ]
    },
    "Chip": {
        "base": "Sample",
        "required": [],
        "custom": [],
        "permitted_children": [
            "SEM_stub",
            "Annealing",
            "Chip",
            "Imaging",
            "XRay_analysis",
            "Electrical_measurement",
            "Micromechanical_testing",
            "Swissmapper"
        ]
    },
    "SEM_stub": {
        "base": "Sample",
        "required": [
            "stub_diameter"
        ],
        "custom": [],
        "permitted_children": [
            "Pillar_array",
            "Tensile_bar",
            "TEM_lamella",
            "Imaging",
            "XRay_analysis",
            "Micromechanical_testing",
            "Swissmapper",
            "Liftout",
            "EBSD",
            "FIB_milling"
        ]
    },
    "TEM_lamella": {
        "base": "Sample",
        "required": [
            "grid_material"
        ],
        "custom": [],
        "permitted_children": [
            "Liftout",
            "Imaging",
            "TKD",
            "APT_tip",
            "EBSD",
            "Micromechanical_testing",
            "FIB_milling"
        ]
    },
    "Pillar_array": {
        "base": "Sample",
        "required": [],
        "custom": [],
        "permitted_children": [
            "TEM_lamella",
            "FIB_milling",
            "Pillar_compression",
            "Imaging",
            "EBSD",
            "Micromechanical_testing",
            "Liftout"
        ]
    },
    "Tensile_bar": {
        "base": "Sample",
        "required": [],
        "custom": [],
        "permitted_children": [
            "TEM_lamella",
            "FIB_milling",
            "Imaging",
            "TKD",
            "EBSD",
            "Micromechanical_testing",
            "Liftout"
        ]
    },
    "APT_tip": {
        "base": "Sample",
        "required": [],
        "custom": [],
        "permitted_children": [
            "FIB_milling",
            "Imaging"
        ]
    },
    "Annealing": {
        "base": "Processing_Step",
        "required": [
            "temperature_C",
            "duration"
        ],
        "custom": [],
        "permitted_children": [
            "Chip",
            "SEM_stub"
        ]
    },
    "FIB_milling": {
        "base": "Processing_Step",
        "required": [
            "ion_species",
            "microscope"
        ],
        "custom": [],
        "permitted_children": []
    },
    "Liftout": {
        "base": "Processing_Step",
        "required": [
            "microscope",
            "ion_species"
        ],
        "custom": [],
        "permitted_children": [
            "TEM_lamella",
            "APT_tip"
        ]
    },
    "Imaging": {
        "base": "Processing_Step",
        "required": [
            "microscope"
        ],
        "custom": [],
        "permitted_children": []
    },
    "XRay_analysis": {
        "base": "Processing_Step",
        "required": [
            "mode"
        ],
        "custom": [],
        "permitted_children": []
    },
    "TKD": {
        "base": "Processing_Step",
        "required": [],
        "custom": [],
        "permitted_children": []
    },
    "EBSD": {
        "base": "Processing_Step",
        "required": [],
        "custom": [],
        "permitted_children": []
    },
    "Micromechanical_testing": {
        "base": "Processing_Step",
        "required": [
            "test_type"
        ],
        "custom": [],
        "permitted_children": []
    },
    "Electrical_measurement": {
        "base": "Processing_Step",
        "required": [],
        "custom": [],
        "permitted_children": []
    },
    "Swissmapper": {
        "base": "Processing_Step",
        "required": [],
        "custom": [],
        "permitted_children": []
    }
}

RESTORED_DEFAULT_SCHEMA = False

def _generate_dynamic_classes():
    global RESTORED_DEFAULT_SCHEMA
    if not os.path.exists(DATABASE_STRUCTURE_FILE):
        update_database_structure(lambda schema: schema.update(deepcopy(DEFAULT_SCHEMA)))
        RESTORED_DEFAULT_SCHEMA = True
    try:
        schema = load_database_structure()
            
        for name, config in schema_class_items(schema):
            if name in ['Sample', 'Processing_Step']:
                continue
                
            base_name = config.get("base")
            if base_name == "Processing_Step":
                base_class = Processing_Step
            else:
                base_class = Sample
                
            req_props = config.get("required", [])
            perm_children = config.get("permitted_children", [])
            
            def make_init(rp, pc, selected_base):
                def __init__(self, **kwargs):
                    selected_base.__init__(self, required_properties=rp, **kwargs)
                    self.permitted_children = pc
                    for prop in rp:
                        if prop in kwargs:
                            setattr(self, prop, kwargs[prop])
                return __init__
                
            new_class = type(name, (base_class,), {
                "__init__": make_init(req_props, perm_children, base_class)
            })
            new_class.__module__ = __name__
            globals()[name] = new_class
    except Exception as e:
        print(f"Failed to generate dynamic classes: {e}")

_generate_dynamic_classes()

def create_class_from_schema(cls_name):
    # This can be called by GUI when a new class is added to re-run the generator
    _generate_dynamic_classes()

def discover_required_properties():
    # Deprecated since JSON schema migration
    pass
