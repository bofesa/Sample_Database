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


class Sample:
    def __init__(self, required_properties=[], **kwargs):
        self.required_properties = required_properties

        # Check if all required properties are provided
        for prop in self.required_properties:
            if prop not in kwargs:
                raise ValueError(f"Missing required property for {self.__class__.__name__}: {prop}")
            
        # # Check if any kwargs look like typos of existing properties
        # with open('database_keys.txt', 'a+') as f:
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
        with open('database_keys.txt', 'a+') as f:
            f.seek(0)
            existing_keys = f.read().splitlines()
            type_prefix = self.__class__.__name__ + '_'
            type_keys = [key[len(type_prefix):] for key in existing_keys if key.startswith(type_prefix)]
            for kwarg_key in kwargs.keys():
                # don't warn for the optional universal 'date' property
                if kwarg_key == 'date':
                    continue
                # Check for possible typos: if the key is similar to an existing key for this type
                # For simplicity, warn if the key is not in type_keys and not in required_properties
                if kwarg_key not in type_keys and kwarg_key not in self.required_properties:
                    print(f"Warning: '{kwarg_key}' is not a known property for {self.__class__.__name__}. Check for typos or add it intentionally.")

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
        # Open the keys file and check if the key already exists
        with open('database_keys.txt', 'a+') as f:
            f.seek(0)
            existing_keys = f.read().splitlines()
            for key in self.properties.keys():
                glob_key = self.__class__.__name__ + '_' + key      # Add the type prefix to the key (how they are stored in the file)
                if glob_key not in existing_keys:
                    f.write(glob_key + '\n')
                    print(f"Added new key: {key} to database_keys.txt")

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

        with open('database_keys.txt', 'a+') as f:
            f.seek(0)
            existing_keys = f.read().splitlines()
            type_prefix = self.__class__.__name__ + '_'
            type_keys = [key[len(type_prefix):] for key in existing_keys if key.startswith(type_prefix)]
            for kwarg_key in kwargs.keys():
                if kwarg_key not in type_keys and kwarg_key not in self.required_properties:
                    print(f"Warning: '{kwarg_key}' is not a known property for {self.__class__.__name__}. Check for typos or add it intentionally.")

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
        # Open the keys file and check if the key already exists
        with open('database_keys.txt', 'a+') as f:
            f.seek(0)
            existing_keys = f.read().splitlines()
            for key in self.properties.keys():
                glob_key = self.__class__.__name__ + '_' + key
                if glob_key not in existing_keys:
                    f.write(glob_key + '\n')
                    print(f"Added new key: {key} to database_keys.txt")

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



def discover_required_properties(output_file='required_properties.txt'):
    """
    Discover required_properties lists for classes defined in this module
    by temporarily intercepting Sample.__init__ and Processing_Step.__init__.
    Writes a text file with one line per class: "ClassName: prop1, prop2..."
    Returns a dict mapping class name -> list of required properties.
    """

    module = sys.modules[__name__]
    captured = {}

    # Keep originals to restore later
    orig_sample_init = Sample.__init__
    orig_proc_init = Processing_Step.__init__

    def _sample_wrapper(self, required_properties=[], **kwargs):
        # Record required properties passed to Sample.__init__
        captured[self.__class__.__name__] = list(required_properties)
        # Do not call original to avoid side-effects during discovery
        return None

    def _proc_wrapper(self, required_properties=[], **kwargs):
        captured[self.__class__.__name__] = list(required_properties)
        return None

    try:
        # Monkey-patch constructors
        Sample.__init__ = _sample_wrapper
        Processing_Step.__init__ = _proc_wrapper

        # Find classes defined in this module
        classes = [obj for _, obj in inspect.getmembers(module, inspect.isclass)
                    if obj.__module__ == module.__name__]

        # Instantiate each class (without kwargs). The patched ctors will capture required_properties.
        for cls in classes:
            try:
                cls()
            except Exception:
                # Ignore instantiation errors; we only need the captured data from our wrappers
                pass
    finally:
        # Restore originals
        Sample.__init__ = orig_sample_init
        Processing_Step.__init__ = orig_proc_init

    # Ensure every class has an entry (empty list if none captured)
    result = {}
    for cls in classes:
        name = cls.__name__
        result[name] = captured.get(name, [])

    # Check if output file exists
    if os.path.exists(output_file):
        # Read old file contents
        with open(output_file, 'r') as f:
            old_lines = f.readlines()
        old_props = {}
        for line in old_lines:
            if ':' in line:
                name, props = line.strip().split(':', 1)
                old_props[name.strip()] = set(p.strip() for p in props.split(',') if p.strip())

        # Compare with new result
        missing = []
        for name in old_props:
            if name in result:
                if not old_props[name].issubset(set(result[name])):
                    missing.append(name)
            else:
                missing.append(name)

        if missing:
            print(f"Warning: The new required_properties list is missing values for: {', '.join(missing)}")
            choice = input("Overwrite file (o) or rename old file (r)? [o/r]: ").strip().lower()
            if choice == 'r':
                timestamp = datetime.datetime.now().strftime('%y%m%d%H%M_')
                new_name = timestamp + output_file
                shutil.move(output_file, new_name)
                print(f"Old file renamed to {new_name}")
            elif choice != 'o':
                print("No action taken.")
                return result

    # Write to file
    with open(output_file, 'w') as f:
        for name in sorted(result.keys()):
            props = ', '.join(result[name])
            f.write(f"{name}: {props}\n")

    return result
