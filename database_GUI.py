from database_classes import *
from datetime import datetime
import colorsys

# -------- GUI + Tree persistence utilities --------

TREE_STORAGE_DIR = "databases"
os.makedirs(TREE_STORAGE_DIR, exist_ok=True)

# ---------- Reflection / dynamic class discovery ----------

def get_sample_classes():
    current_globals = globals()
    base = current_globals.get("Sample")
    if base is None:
        return {}
    result = {}
    for name, obj in current_globals.items():
        if inspect.isclass(obj) and issubclass(obj, base) and obj is not base:
            result[name] = obj
    return result


# ---------- Permitted children resolution ----------

def resolve_permitted_children(sample_obj):
    out = []
    pcs = getattr(sample_obj, "permitted_children", [])
    for c in pcs:
        if inspect.isclass(c):
            out.append(c.__name__)
        else:
            out.append(str(c))
    return sorted(out, key=lambda s: s.lower())

# ---------- Serialization ----------

def serialize_tree(tree, filename):
    ''' Save a tree to JSON file '''
    data = {}
    nodes = []
    for n in tree.all_nodes_itr():
        if n.tag == "SYSTEM":
            data["root"] = {
                "id": n.identifier,
                "sample_system": n.data.get("Sample_System")
            }
        else:
            obj = n.data["obj"]
            nodes.append({
                "id": n.identifier,
                "parent": tree.parent(n.identifier).identifier if tree.parent(n.identifier) else None,
                "class": obj.__class__.__name__,
                "id": obj.id,
                "entry_created_date": obj.entry_created_date,
                "properties": obj.properties
            })
    data["nodes"] = nodes
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return filename

def deserialize_tree(filename):
    ''' Load a tree from JSON file '''
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    tree = treelib.Tree()
    root_id = data["root"]["id"]
    tree.create_node(tag="SYSTEM", identifier=root_id, data={"Sample_System": data["root"]["sample_system"]})
    classes = get_sample_classes()
    # Temporarily suppress key logging to avoid duplicates on load
    for node_spec in data["nodes"]:
        cls_name = node_spec["class"]
        cls = classes.get(cls_name)
        if cls is None:
            continue
        original_log = cls.log_keys
        cls.log_keys = lambda *args, **kwargs: None
        obj = cls(**deepcopy(node_spec["properties"]))
        cls.log_keys = original_log
        # Override immutable fields
        obj._id = node_spec["id"]
        obj._entry_created_date = node_spec["entry_created_date"]
        tree.create_node(tag=cls_name,
                         identifier=obj.id,
                         parent=node_spec["parent"],
                         data={"obj": obj})
    return tree

# ---------- Utility to build kwargs via dialog ----------

class PropertyEditor(tk.Toplevel):
    def __init__(self, master, sample_class, existing_keys, required_props):
        super().__init__(master)
        self.title(f"Properties for {sample_class.__name__}")
        self.sample_class = sample_class
        self.result = None
        self.req = required_props
        self.geometry("420x380")
        self.resizable(False, True)

        self.prop_frame = ttk.Frame(self)
        self.prop_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.rows = []  # (key_var, val_var, key_cb)
        ttk.Label(self.prop_frame, text="Required properties:").grid(row=0, column=0, columnspan=3, sticky="w")

        self.existing_keys = sorted(existing_keys)
        self.existing_keys.append("<New property...>")
        r = 1
        for rp in self.req:
            kv = tk.StringVar(value=rp)
            vv = tk.StringVar()
            cb = ttk.Combobox(self.prop_frame, values=[rp], textvariable=kv, state="readonly", width=22)
            cb.grid(row=r, column=0, padx=2, pady=2, sticky="w")
            ent = ttk.Entry(self.prop_frame, textvariable=vv, width=28)
            ent.grid(row=r, column=1, padx=2, pady=2, sticky="w")
            self.rows.append((kv, vv, cb))
            r += 1

        ttk.Separator(self.prop_frame).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6)
        r += 1
        ttk.Label(self.prop_frame, text="Optional properties:").grid(row=r, column=0, columnspan=3, sticky="w")
        r += 1

        self.opt_container = ttk.Frame(self.prop_frame)
        self.opt_container.grid(row=r, column=0, columnspan=3, sticky="ew")
        r += 1

        btn_add = ttk.Button(self.prop_frame, text="Add property row", command=self.add_optional_row)
        btn_add.grid(row=r, column=0, sticky="w", pady=6)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=4)
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side="left", padx=5)

        self.add_optional_row()

    def add_optional_row(self):
        # Determine next available row index inside the optional container by inspecting existing widgets' rows
        existing_rows = [int(w.grid_info().get('row', 0)) for w in self.opt_container.grid_slaves()]
        row_index = max(existing_rows) + 1 if existing_rows else 0

        kv = tk.StringVar()
        vv = tk.StringVar()
        cb = ttk.Combobox(self.opt_container, values=self.existing_keys, textvariable=kv, width=22)
        cb.grid(row=row_index, column=0, padx=2, pady=2, sticky="w")
        ent = ttk.Entry(self.opt_container, textvariable=vv, width=28)
        ent.grid(row=row_index, column=1, padx=2, pady=2, sticky="w")

        def on_select(_event):
            if kv.get() == "<New property...>":
                new_key = simpledialog.askstring("New property", "Enter new property name:", parent=self)
                if new_key:
                    # Insert before sentinel if not already present
                    if new_key not in self.existing_keys:
                        self.existing_keys.insert(-1, new_key)
                    kv.set(new_key)
                    # Update all combobox values to include the new key
                    for rset in self.rows:
                        try:
                            rset[2]['values'] = self.existing_keys
                        except Exception:
                            pass
                    for child in self.opt_container.winfo_children():
                        if isinstance(child, ttk.Combobox):
                            child['values'] = self.existing_keys

        cb.bind("<<ComboboxSelected>>", on_select)
        self.rows.append((kv, vv, cb))

    def on_ok(self):
        props = {}
        # Collect required
        for kv, vv, _ in self.rows:
            k = kv.get().strip()
            v = vv.get()
            if not k:
                continue
            if k in props:
                messagebox.showerror("Error", f"Duplicate property key: {k}")
                return
            props[k] = v
        # Validate required
        missing = [r for r in self.req if r not in props or props[r] == ""]
        if missing:
            messagebox.showerror("Missing", f"Missing required properties: {', '.join(missing)}")
            return
        self.result = props
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

# ---------- Main GUI ----------

class SampleTreeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sample Tree Manager")
        self.tree_obj = None
        self.current_file = None
        self.discover_btn = None
        self.display_mode = "single"
        self.multi_trees = {}
        self.treeview_index = {}
        self.treeview_system_iids = {}

        main = ttk.Frame(root)
        main.pack(fill="both", expand=True, padx=6, pady=6)

        # Add a vertical scrollbar to the main treeview
        treeview_frame = ttk.Frame(main)
        treeview_frame.pack(fill="both", expand=True, pady=6)
        self.treeview = ttk.Treeview(treeview_frame)
        self.treeview.pack(side="left", fill="both", expand=True)
        treeview_scrollbar = ttk.Scrollbar(treeview_frame, orient="vertical", command=self.treeview.yview)
        treeview_scrollbar.pack(side="right", fill="y")
        self.treeview.configure(yscrollcommand=treeview_scrollbar.set)

        top_bar = ttk.Frame(main)
        top_bar.pack(fill="x")
        ttk.Button(top_bar, text="New Tree", command=self.create_new_tree).pack(side="left", padx=2)
        ttk.Button(top_bar, text="Load Tree", command=self.load_tree).pack(side="left", padx=2)
        ttk.Button(top_bar, text="Open All Trees", command=self.load_all_trees).pack(side="left", padx=2)
        ttk.Button(top_bar, text="Save Tree", command=self.save_tree).pack(side="left", padx=2)

        ttk.Button(top_bar, text="Search", command=self.search_property).pack(side="right", padx=2)

        # # Create the discover button alongside the other top-bar buttons (obsolete when wrapped into exe)
        # try:
        #     self.discover_btn = ttk.Button(top_bar, text="Discover required properties", command=self._on_discover_click)
        #     self.discover_btn.pack(side="left", padx=2)
        # except Exception:
        #     self.discover_btn = None

        # Rainbow mode is available for single-tree view only.
        self.rainbow_active = False
        self.rainbow_button = ttk.Button(top_bar, text="Rainbow Mode", command=self.toggle_rainbow_mode)
        self.rainbow_button.pack_forget()

        self.treeview.bind("<<TreeviewSelect>>", self.on_select)
        self.treeview.bind("<<TreeviewOpen>>", self.on_treeview_open)

        # Node editor frame
        action_frame = ttk.LabelFrame(main, text="Add Child")
        action_frame.pack(fill="x", pady=4)

        ttk.Label(action_frame, text="Parent Node:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.parent_label_var = tk.StringVar(value="-")
        ttk.Label(action_frame, textvariable=self.parent_label_var).grid(row=0, column=1, sticky="w", padx=2, pady=2)

        ttk.Label(action_frame, text="Child Class:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        self.class_var = tk.StringVar()
        self.class_cb = ttk.Combobox(action_frame, textvariable=self.class_var, width=28, state="readonly")
        self.class_cb.grid(row=1, column=1, sticky="w", padx=2, pady=2)

        ttk.Button(action_frame, text="View Properties", command=self.view_properties).grid(row=2, column=0, padx=2, pady=6, sticky="w")
        ttk.Button(action_frame, text="Edit Node", command=self.edit_node).grid(row=2, column=1, padx=2, pady=6, sticky="w")
        ttk.Button(action_frame, text="Create Node", command=self.add_child_node).grid(row=2, column=1, padx=2, pady=6, sticky="e")

        self.status_var = tk.StringVar()
        ttk.Label(main, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x")

        # Save with timestamp button below Add Child
        save_frame = ttk.Frame(main)
        save_frame.pack(fill="x", pady=(6, 0))
        ttk.Button(save_frame, text="Save with Timestamp and Close", command=self._save_with_timestamp_and_close).pack(padx=2, pady=6, anchor="center")

        self.refresh_status("Ready")

    def refresh_status(self, msg):
        self.status_var.set(msg)

    def _reset_multi_state(self):
        self.multi_trees = {}
        self.treeview_index = {}
        self.treeview_system_iids = {}

    def _clear_loaded_trees(self):
        self.tree_obj = None
        self.current_file = None
        self.display_mode = "single"
        self._reset_multi_state()
        self.treeview.delete(*self.treeview.get_children())
        self.parent_label_var.set("-")
        self.class_cb['values'] = []
        self.class_var.set("")
        self.rainbow_active = False
        self.rainbow_button.pack_forget()
        self.rainbow_button.config(text="Rainbow Mode")

    def _selected_node_context(self):
        sel = self.treeview.selection()
        if not sel:
            return None
        tv_iid = sel[0]

        if self.display_mode == "single":
            if not self.tree_obj:
                return None
            node = self.tree_obj.get_node(tv_iid)
            if node is None:
                return None
            return {
                "tree": self.tree_obj,
                "node": node,
                "node_id": node.identifier,
                "system_key": "single",
                "file": self.current_file,
                "is_system_root": node.identifier == self.tree_obj.root,
                "tv_iid": tv_iid,
            }

        payload = self.treeview_index.get(tv_iid)
        if not payload:
            return None
        system_key = payload["system_key"]
        node_id = payload["node_id"]
        system_info = self.multi_trees.get(system_key)
        if not system_info:
            return None
        tree = system_info["tree"]
        node = tree.get_node(node_id)
        if node is None:
            return None
        return {
            "tree": tree,
            "node": node,
            "node_id": node_id,
            "system_key": system_key,
            "file": system_info["file"],
            "is_system_root": node_id == tree.root,
            "tv_iid": tv_iid,
        }

    def _multi_tree_iid(self, system_key, node_id):
        root_iid = self.treeview_system_iids.get(system_key)
        if not root_iid:
            return None
        tree = self.multi_trees[system_key]["tree"]
        if node_id == tree.root:
            return root_iid
        return f"{root_iid}::{node_id}"

    def _refresh_after_tree_change(self, system_key=None, focus_node_id=None):
        if self.display_mode == "multi":
            self.populate_multi_treeview(expand_system_key=system_key, focus_node_id=focus_node_id)
        else:
            self.populate_treeview()

    def _hide_discover_button(self):
        if self.discover_btn:
            try:
                self.discover_btn.pack_forget()
            except Exception:
                try:
                    self.discover_btn.destroy()
                except Exception:
                    pass
            self.discover_btn = None

    def create_new_tree(self):
        sample_system = simpledialog.askstring("Sample System", "Sample System:", parent=self.root)
        if not sample_system:
            return
        self.display_mode = "single"
        self._reset_multi_state()
        self.tree_obj = treelib.Tree()
        root_id = "SYSTEM"
        self.tree_obj.create_node("SYSTEM", root_id, data={"Sample_System": sample_system})
        self.current_file = filedialog.asksaveasfilename(
            initialdir=TREE_STORAGE_DIR,
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title="Save New Tree")
        if not self.current_file:
            self.tree_obj = None
            return
        serialize_tree(self.tree_obj, self.current_file)
        self.populate_treeview()
        # hide discover button once a tree exists / is created
        self._hide_discover_button()
        self.refresh_status("New tree created.")

    def load_tree(self):
        filename = filedialog.askopenfilename(
            initialdir=TREE_STORAGE_DIR,
            filetypes=[("JSON Files", "*.json")],
            title="Load Tree")
        if not filename:
            return
        try:
            self.display_mode = "single"
            self._reset_multi_state()
            self.tree_obj = deserialize_tree(filename)
            self.current_file = filename
            self.populate_treeview()
            # hide discover button once a tree is loaded
            self._hide_discover_button()
            self.refresh_status(f"Loaded {os.path.basename(filename)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")

    def load_all_trees(self):
        files = []
        try:
            for name in sorted(os.listdir(TREE_STORAGE_DIR)):
                path = os.path.join(TREE_STORAGE_DIR, name)
                if not os.path.isfile(path):
                    continue
                if not name.lower().endswith(".json"):
                    continue
                files.append(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan databases folder: {e}")
            return

        if not files:
            messagebox.showwarning("No Trees", "No JSON tree files found in databases folder.")
            return

        loaded = {}
        failed = []
        for idx, path in enumerate(files):
            try:
                tree = deserialize_tree(path)
                system_node = tree.get_node(tree.root)
                system_name = ""
                if system_node is not None:
                    system_name = system_node.data.get("Sample_System", "")
                key = f"{idx:04d}_{os.path.basename(path)}"
                loaded[key] = {
                    "tree": tree,
                    "file": path,
                    "label": f"{system_name}" if system_name else os.path.basename(path),
                }
            except Exception as e:
                failed.append(f"{os.path.basename(path)}: {e}")

        if not loaded:
            messagebox.showerror("Error", "No trees could be loaded.")
            return

        self.display_mode = "multi"
        self.tree_obj = None
        self.current_file = None
        self.multi_trees = loaded
        try:
            self.rainbow_button.pack(side="left", padx=2)
        except Exception:
            pass
        self.populate_multi_treeview()
        self.parent_label_var.set("-")
        self.class_cb['values'] = []
        self.class_var.set("")
        self._hide_discover_button()

        if failed:
            self.refresh_status(f"Loaded {len(loaded)} trees ({len(failed)} failed).")
        else:
            self.refresh_status(f"Loaded {len(loaded)} trees.")

    def save_tree(self):
        if self.display_mode == "multi":
            if not self.multi_trees:
                messagebox.showwarning("Save", "No trees to save.")
                return
            saved = 0
            for info in self.multi_trees.values():
                serialize_tree(info["tree"], info["file"])
                saved += 1
            self.refresh_status(f"Saved {saved} trees.")
            return

        if not self.tree_obj:
            return
        if not self.current_file:
            self.current_file = filedialog.asksaveasfilename(
                initialdir=TREE_STORAGE_DIR,
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json")])
            if not self.current_file:
                return
        serialize_tree(self.tree_obj, self.current_file)
        self.refresh_status("Tree saved.")
    
    # ---------- Discover Required Properties Option (integrated into GUI) ----------
    def _on_discover_click(self):
        try:
            discover_required_properties()
        except NameError:
            messagebox.showerror("Error", "discover_required_properties is not available.")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to discover required properties: {e}")
            return
        try:
            self.discover_btn.destroy()
        except Exception:
            pass
        self.discover_btn = None
        messagebox.showinfo("Discovered", "Required properties were successfully discovered.")

    
    # ---------- Build the treeview display ----------
    def rainbow_colours(self):
        return [
            "#000000",  # black
            "#FF0000",  # red
            "#FF7F00",  # orange
            "#00FF00",  # green
            "#00FFFF",  # cyan
            "#0000FF",  # blue
            "#7F00FF",  # violet
            "#FFBF00",  # amber
            "#BFFF00",  # chartreuse
            "#00FF80",  # aquamarine
            "#0080FF",  # azure
            "#4000FF",  # indigo
            "#FF00BF",  # rose
        ]

    def _activate_rainbow_mode(self, colours):
        try:
            self.treeview.delete(*self.treeview.get_children())
            if not self.tree_obj:
                return

            def add(node_id, depth=0):
                node = self.tree_obj.get_node(node_id)
                if node is None:
                    return
                parent = self.tree_obj.parent(node_id)
                parent_tv = "" if parent is None else parent.identifier
                text = self.node_text(node)
                color_tag = f"rainbow_{depth % len(colours)}"
                try:
                    self.treeview.tag_configure(color_tag, foreground=colours[depth % len(colours)])
                except Exception:
                    pass
                self.treeview.insert(parent_tv, "end", iid=node.identifier, text=text, tags=(color_tag,))
                try:
                    self.treeview.item(node.identifier, open=True)
                except Exception:
                    pass
                for child in self.tree_obj.children(node_id):
                    add(child.identifier, depth + 1)

            add(self.tree_obj.root)
            for iid in self.treeview.get_children():
                try:
                    self.treeview.item(iid, open=True)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Error", f"Failed to activate rainbow mode: {e}")

    def toggle_rainbow_mode(self):
        has_single = self.display_mode == "single" and self.tree_obj is not None
        has_multi = self.display_mode == "multi" and bool(self.multi_trees)
        if not (has_single or has_multi):
            messagebox.showinfo("Rainbow Mode", "Load a tree first.")
            return
        if not self.rainbow_active:
            self.rainbow_active = True
            if self.display_mode == "single":
                self._activate_rainbow_mode(self.rainbow_colours())
            else:
                self.populate_multi_treeview()
            self.rainbow_button.config(text="Classic View")
        else:
            self.rainbow_active = False
            if self.display_mode == "single":
                self.populate_treeview()
            else:
                self.populate_multi_treeview()
            self.rainbow_button.config(text="Rainbow Mode")

    def populate_treeview(self):
        self.treeview_index = {}
        self.treeview_system_iids = {}

        if self.display_mode == "multi":
            self.populate_multi_treeview()
            return

        if self.rainbow_active:
            self._activate_rainbow_mode(self.rainbow_colours())
            return

        self.treeview.delete(*self.treeview.get_children())
        if not self.tree_obj:
            return

        try:
            self.rainbow_button.pack(side="left", padx=2)
        except Exception:
            pass

        # configure tag for system children (red text)
        try:
            self.treeview.tag_configure("system_child", foreground="red")
        except Exception:
            # Some environments may not support tag_configure; ignore safely
            pass

        # Build hierarchical insertion and expand every node as it's added
        def add(node_id):
            node = self.tree_obj.get_node(node_id)
            parent = self.tree_obj.parent(node_id)
            parent_tv = "" if parent is None else parent.identifier
            text = self.node_text(node)

            # mark direct children of the SYSTEM root with the "system_child" tag
            tags = ()
            try:
                if parent is not None and parent.identifier == self.tree_obj.root and node.tag != "SYSTEM":
                    tags = ("system_child",)
            except Exception:
                tags = ()

            self.treeview.insert(parent_tv, "end", iid=node.identifier, text=text, tags=tags)
            # ensure the inserted node is expanded
            try:
                self.treeview.item(node.identifier, open=True)
            except Exception:
                pass
            for child in self.tree_obj.children(node_id):
                add(child.identifier)
        add(self.tree_obj.root)
        # make sure top-level items are expanded as well
        try:
            for iid in self.treeview.get_children():
                self.treeview.item(iid, open=True)
        except Exception:
            pass

    def populate_multi_treeview(self, expand_system_key=None, focus_node_id=None):
        self.treeview.delete(*self.treeview.get_children())
        self.treeview_index = {}
        self.treeview_system_iids = {}

        if not self.multi_trees:
            return

        try:
            self.rainbow_button.pack(side="left", padx=2)
        except Exception:
            pass

        def add_node(system_key, tree, node_id, parent_iid, expand_this_system, depth):
            node = tree.get_node(node_id)
            node_iid = self._multi_tree_iid(system_key, node_id)
            if node_iid is None or node is None:
                return
            tags = ()
            if self.rainbow_active:
                color_tag = f"rainbow_{depth % len(self.rainbow_colours())}"
                tags = (color_tag,)
                try:
                    self.treeview.tag_configure(color_tag, foreground=self.rainbow_colours()[depth % len(self.rainbow_colours())])
                except Exception:
                    pass
            else:
                parent = tree.parent(node_id)
                try:
                    if parent is not None and parent.identifier == tree.root and node.tag != "SYSTEM":
                        tags = ("system_child",)
                except Exception:
                    tags = ()
            self.treeview.insert(parent_iid, "end", iid=node_iid, text=self.node_text(node), tags=tags)
            self.treeview.item(node_iid, open=bool(expand_this_system))
            self.treeview_index[node_iid] = {"system_key": system_key, "node_id": node_id}
            for child in tree.children(node_id):
                add_node(system_key, tree, child.identifier, node_iid, expand_this_system, depth + 1)

        try:
            self.treeview.tag_configure("system_child", foreground="red")
        except Exception:
            pass

        for system_key in sorted(self.multi_trees.keys()):
            info = self.multi_trees[system_key]
            tree = info["tree"]
            root_node = tree.get_node(tree.root)
            top_iid = f"SYS::{system_key}"
            self.treeview_system_iids[system_key] = top_iid
            label = info.get("label", "")
            display_name = label if label else "SYSTEM"
            top_text = f"{self.node_text(root_node)} - {os.path.basename(info['file'])}"
            if root_node and root_node.data.get("Sample_System"):
                top_text = f"SYSTEM ({display_name}) - {os.path.basename(info['file'])}"
            top_tags = ()
            if self.rainbow_active:
                top_color_tag = "rainbow_0"
                top_tags = (top_color_tag,)
                try:
                    self.treeview.tag_configure(top_color_tag, foreground=self.rainbow_colours()[0])
                except Exception:
                    pass
            self.treeview.insert("", "end", iid=top_iid, text=top_text, tags=top_tags)
            self.treeview.item(top_iid, open=bool(expand_system_key and expand_system_key == system_key))
            self.treeview_index[top_iid] = {"system_key": system_key, "node_id": tree.root}
            for child in tree.children(tree.root):
                add_node(system_key, tree, child.identifier, top_iid, expand_system_key and expand_system_key == system_key, 1)

        if focus_node_id and expand_system_key:
            tree = self.multi_trees.get(expand_system_key, {}).get("tree")
            if tree:
                path = []
                cur = focus_node_id
                while True:
                    node = tree.get_node(cur)
                    if node is None:
                        break
                    path.append(cur)
                    parent = tree.parent(cur)
                    if parent is None:
                        break
                    cur = parent.identifier
                for nid in reversed(path):
                    iid = self._multi_tree_iid(expand_system_key, nid)
                    if iid:
                        try:
                            self.treeview.item(iid, open=True)
                        except Exception:
                            pass
                target_iid = self._multi_tree_iid(expand_system_key, focus_node_id)
                if target_iid:
                    try:
                        self.treeview.selection_set(target_iid)
                        self.treeview.see(target_iid)
                    except Exception:
                        pass

    def _expand_all_descendants(self, iid):
        for child in self.treeview.get_children(iid):
            try:
                self.treeview.item(child, open=True)
            except Exception:
                pass
            self._expand_all_descendants(child)

    def on_treeview_open(self, _event):
        if self.display_mode != "multi":
            return
        sel = self.treeview.selection()
        opened_iid = sel[0] if sel else self.treeview.focus()
        if not opened_iid:
            return
        payload = self.treeview_index.get(opened_iid)
        if not payload:
            return
        system_key = payload.get("system_key")
        node_id = payload.get("node_id")
        info = self.multi_trees.get(system_key)
        if not info:
            return
        tree = info.get("tree")
        if not tree:
            return
        if node_id == tree.root:
            self._expand_all_descendants(opened_iid)

    def node_text(self, node):
        ''' Generate display text for a tree node '''
        tag = node.tag
        if tag == "SYSTEM":
            text = f"SYSTEM ({node.data.get('Sample_System')})"
        else:
            obj = node.data["obj"]
            text = f"{tag} [{obj.id}]"
            # append material and/or name properties if present
            # Find material
            mat = None
            try:
                props = getattr(obj, "properties", {})
                if isinstance(props, dict):
                    mat = props.get("material")
                if mat is None:
                    mat = getattr(obj, "material", None)
            except Exception:
                mat = None
            if mat not in (None, ""):
                mattext = f": {mat}"
            else:
                mattext = ""
            # Find name
            nam = None
            try:
                props = getattr(obj, "properties", {})
                if isinstance(props, dict):
                    nam = props.get("name")
                if nam is None:
                    nam = getattr(obj, "name", None)
            except Exception:
                nam = None
            if nam not in (None, ""):
                namtext = f" ({nam})"
            else:
                namtext = ""
            text += mattext + namtext
            # Special cases for certain classes to append extra info
            try:
                if obj.__class__.__name__ == "Annealing":
                    props = getattr(obj, "properties", {})
                    if isinstance(props, dict):
                        temp = props.get("temperature_C")
                        if temp not in (None, ""):
                            text += f" ({temp}\u00B0C)"
                if obj.__class__.__name__ == "Micromechanical_testing":
                    props = getattr(obj, "properties", {})
                    if isinstance(props, dict):
                        test_type = props.get("test_type")
                        if test_type not in (None, ""):
                            text += f" ({test_type})"
            except Exception:
                pass
        return text
    
    def edit_node(self):
        ctx = self._selected_node_context()
        if not ctx:
            messagebox.showwarning("Select", "Select a node first.")
            return
        node_id = ctx["node_id"]
        node = ctx["node"]
        tree_obj = ctx["tree"]
        if node is None:
            messagebox.showerror("Error", "Selected node not found in tree.")
            return
        if node.tag == "SYSTEM":
            messagebox.showwarning("Edit", "SYSTEM node cannot be edited.")
            return

        obj = node.data.get("obj")
        if obj is None:
            messagebox.showerror("Error", "No object data for selected node.")
            return

        class_name = node.tag
        cls = obj.__class__

        # Load required properties (reuse same logic as add_child_node)
        try:
            with open("required_properties.txt", "r", encoding="utf-8") as f:
                txt = f.read().strip()
            if not txt:
                subclass_req_map = {}
            else:
                try:
                    subclass_req_map = json.loads(txt)
                    if not isinstance(subclass_req_map, dict):
                        raise ValueError("JSON root is not an object")
                except Exception:
                    subclass_req_map = {}
                    for line in txt.splitlines():
                        line = line.split("#", 1)[0].strip()
                        if not line:
                            continue
                        if ":" in line:
                            cls_key, vals = line.split(":", 1)
                        elif "=" in line:
                            cls_key, vals = line.split("=", 1)
                        else:
                            parts = line.split()
                            if len(parts) == 2:
                                cls_key, vals = parts[0], parts[1]
                            else:
                                continue
                        keys = [k.strip() for k in vals.split(",") if k.strip()]
                        subclass_req_map[cls_key.strip()] = keys
        except FileNotFoundError:
            subclass_req_map = {}
        required = subclass_req_map.get(class_name, [])

        # Collect existing keys for dropdown (filter by prefix type_)
        existing_keys = []
        if os.path.exists("database_keys.txt"):
            with open("database_keys.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(class_name + "_"):
                        existing_keys.append(line[len(class_name) + 1:])

        # Include current object's property keys as available existing keys
        cur_props = obj.properties if isinstance(obj.properties, dict) else {}
        existing_keys = sorted(set(existing_keys) | set(cur_props.keys()))

        editor = PropertyEditor(self.root, cls, set(existing_keys), required)

        # Prefill required rows with current values
        try:
            for i, rp in enumerate(required):
                if i < len(editor.rows):
                    kv, vv, _cb = editor.rows[i]
                    kv.set(rp)
                    vv.set(cur_props.get(rp, ""))
        except Exception:
            pass

        # Prefill optional rows with remaining current properties
        try:
            opt_props = {k: v for k, v in cur_props.items() if k not in required}
            opt_index = len(required)
            for k, v in opt_props.items():
                if opt_index >= len(editor.rows):
                    editor.add_optional_row()
                kv, vv, _cb = editor.rows[opt_index]
                kv.set(k)
                vv.set(v)
                opt_index += 1
        except Exception:
            pass

        self.root.wait_window(editor)
        if editor.result is None:
            return

        new_props = editor.result
        try:
            # Try to set properties back onto object
            if hasattr(obj, "properties"):
                obj.properties = new_props
            else:
                setattr(obj, "properties", new_props)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update properties: {e}")
            return

        # Refresh treeview to reflect any changes
        self._refresh_after_tree_change(system_key=ctx["system_key"], focus_node_id=node_id)
        if self.display_mode == "multi":
            self.refresh_status(f"Edited {class_name} node in {os.path.basename(ctx['file'])}.")
        else:
            self.refresh_status(f"Edited {class_name} node.")

    def _save_with_timestamp_and_close(self):
        self.save_tree()
        if self.display_mode == "multi":
            if not self.multi_trees:
                messagebox.showwarning("Save", "No trees to save.")
                return
            archive_dir = os.path.join(TREE_STORAGE_DIR, "archive")
            os.makedirs(archive_dir, exist_ok=True)
            ts = datetime.now().strftime("%y%m%d")
            try:
                for info in self.multi_trees.values():
                    base = os.path.basename(info["file"])
                    root, ext = os.path.splitext(base)
                    out_name = f"{root}_{ts}{ext}" if ext else f"{root}_{ts}"
                    out_path = os.path.join(archive_dir, out_name)
                    serialize_tree(info["tree"], out_path)
                self._clear_loaded_trees()
                self.refresh_status("Ready")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to archive trees: {e}")
            return

        if not self.tree_obj:
            messagebox.showwarning("Save", "No tree to save.")
            return
        base_file = self.current_file
        if not base_file:
            base_file = filedialog.asksaveasfilename(
                initialdir=TREE_STORAGE_DIR,
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json")],
                title="Save Tree As")
        if not base_file:
            return
        # Ensure archive subdirectory exists
        archive_dir = os.path.join(TREE_STORAGE_DIR, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        # Add timestamp to filename and move to archive
        base_file = os.path.join(archive_dir, os.path.basename(base_file))
        ts = datetime.now().strftime("%y%m%d")
        root, ext = os.path.splitext(base_file)
        new_filename = f"{root}_{ts}{ext}" if ext else f"{root}_{ts}"
        try:
            serialize_tree(self.tree_obj, new_filename)
            self.refresh_status(f"Saved as {os.path.basename(new_filename)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
            return
        try:
            self._clear_loaded_trees()
            self.refresh_status("Ready")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to close tree: {e}")

    def on_select(self, _event):
        ctx = self._selected_node_context()
        if not ctx:
            self.parent_label_var.set("-")
            self.class_cb['values'] = []
            self.class_var.set("")
            return
        parent_label = ctx["node_id"]
        if self.display_mode == "multi":
            parent_label = f"{os.path.basename(ctx['file'])}: {ctx['node_id']}"
        self.parent_label_var.set(parent_label)
        self.populate_child_class_options(ctx["tree"], ctx["node_id"])

    def populate_child_class_options(self, tree_obj, parent_id):
        if parent_id == tree_obj.root:
            # root can have any top-level sample
            classes = sorted(get_sample_classes().keys())
        else:
            parent_node = tree_obj.get_node(parent_id)
            parent_obj = parent_node.data["obj"]
            permitted = resolve_permitted_children(parent_obj)
            # Convert to only those classes actually available
            classes_available = get_sample_classes()
            classes = [c for c in permitted if c in classes_available]
        self.class_cb['values'] = classes
        if classes:
            self.class_var.set(classes[0])
        else:
            self.class_var.set("")

    def add_child_node(self):
        ctx = self._selected_node_context()
        if not ctx:
            messagebox.showwarning("Select", "Select a parent node first.")
            return
        tree_obj = ctx["tree"]
        parent_id = ctx["node_id"]
        class_name = self.class_var.get()
        if not class_name:
            messagebox.showwarning("Class", "No child class available.")
            return
        classes = get_sample_classes()
        cls = classes[class_name]

        # Do not allow Processing_Step (or its subclasses) as direct children of the top Sample System node
        try:
            root_id = tree_obj.root
            base_ps = globals().get("Processing_Step")
            # fallback: search globals for a class named "Processing_Step"
            if base_ps is None:
                for obj in globals().values():
                    if inspect.isclass(obj) and obj.__name__ == "Processing_Step":
                        base_ps = obj
                        break
            if parent_id == root_id and base_ps and inspect.isclass(base_ps) and issubclass(cls, base_ps):
                messagebox.showwarning("Not allowed", "Processing Steps cannot be direct children of the top Sample System node.")
                return
        except Exception:
            pass

        # Determine required properties from file
        try:
            with open("required_properties.txt", "r", encoding="utf-8") as f:
                txt = f.read().strip()
                if not txt:
                    subclass_req_map = {}
                else:
                    try:
                        subclass_req_map = json.loads(txt)
                        if not isinstance(subclass_req_map, dict):
                            raise ValueError("JSON root is not an object")
                    except Exception:
                        subclass_req_map = {}
                        for line in txt.splitlines():
                            line = line.split("#", 1)[0].strip()  # allow comments with #
                            if not line:
                                continue
                            if ":" in line:
                                cls_key, vals = line.split(":", 1)
                            elif "=" in line:
                                cls_key, vals = line.split("=", 1)
                            else:
                                # single-class single-key line
                                parts = line.split()
                                if len(parts) == 2:
                                    cls_key, vals = parts[0], parts[1]
                                else:
                                    continue
                            keys = [k.strip() for k in vals.split(",") if k.strip()]
                            subclass_req_map[cls_key.strip()] = keys
        except FileNotFoundError:
            subclass_req_map = {}
        required = subclass_req_map.get(class_name, [])

        # Collect existing keys for dropdown (filter by prefix type_)
        existing_keys = []
        if os.path.exists("database_keys.txt"):
            with open("database_keys.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(class_name + "_"):
                        existing_keys.append(line[len(class_name) + 1:])

        editor = PropertyEditor(self.root, cls, set(existing_keys), required)
        self.root.wait_window(editor)
        if editor.result is None:
            return
        kwargs = editor.result
        try:
            obj = cls(**kwargs)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create instance: {e}")
            return
        tree_obj.create_node(tag=class_name,
                      identifier=obj.id,
                      parent=parent_id,
                      data={"obj": obj})
        self._refresh_after_tree_change(system_key=ctx["system_key"], focus_node_id=obj.id)
        if self.display_mode == "multi":
            self.refresh_status(f"Added {class_name} node in {os.path.basename(ctx['file'])}.")
        else:
            self.refresh_status(f"Added {class_name} node.")

    def view_properties(self):
        ctx = self._selected_node_context()
        if not ctx:
            messagebox.showwarning("Select", "Select a node first.")
            return
        node_id = ctx["node_id"]
        node = ctx["node"]
        if node is None:
            messagebox.showerror("Error", "Selected node not found in tree.")
            return

        if node.tag == "SYSTEM":
            info = {"node": "SYSTEM", "Sample_System": node.data.get("Sample_System")}
        else:
            obj = node.data.get("obj")
            if obj is None:
                messagebox.showerror("Error", "No object data for selected node.")
                return
            info = {
                "class": node.tag,
                "id": getattr(obj, "id", None),
                "entry_created_date": getattr(obj, "entry_created_date", None),
                "properties": getattr(obj, "properties", {})
            }

        # Table-based viewer window
        class PropertiesTables(tk.Toplevel):
            def __init__(self, master, title, summary_dict, prop_keys):
                super().__init__(master)
                self.title(title)
                self.geometry("640x420")
                self.resizable(True, True)

                container = ttk.Frame(self)
                container.pack(fill="both", expand=True, padx=8, pady=8)

                # Top table: summary (all non-kwarg values)
                ttk.Label(container, text="Summary").pack(anchor="w")
                top_frame = ttk.Frame(container)
                top_frame.pack(fill="x", pady=(2, 8))

                top_tree = ttk.Treeview(
                    top_frame,
                    columns=("property", "value"),
                    show="tree",  # hide column headings
                    displaycolumns=("property", "value"),
                    height=6
                )
                # hide the implicit #0 tree column visually
                top_tree.column("#0", width=0, stretch=False)
                # top_tree.heading("property", text="Property")
                # top_tree.heading("value", text="Value")
                top_tree.column("property", width=220, anchor="w")
                top_tree.column("value", width=380, anchor="w")

                top_vsb = ttk.Scrollbar(top_frame, orient="vertical", command=top_tree.yview)
                top_tree.configure(yscrollcommand=top_vsb.set)
                top_vsb.pack(side="right", fill="y")
                top_tree.pack(fill="x", expand=True)

                for k, v in summary_dict.items():
                    top_tree.insert("", "end", values=(k, "" if v is None else str(v)))

                # Bottom table: properties keys and values
                ttk.Label(container, text="Properties").pack(anchor="w")
                prop_frame = ttk.Frame(container)
                prop_frame.pack(fill="both", expand=True)

                prop_tree = ttk.Treeview(prop_frame, columns=("property", "value"), show="tree", displaycolumns=("property", "value"))
                # hide the implicit #0 tree column visually
                prop_tree.column("#0", width=0, stretch=False)
                # prop_tree.heading("property", text="Property")
                # prop_tree.heading("value", text="Value")
                prop_tree.column("property", width=220, anchor="w")
                prop_tree.column("value", width=380, anchor="w")

                prop_vsb = ttk.Scrollbar(prop_frame, orient="vertical", command=prop_tree.yview)
                prop_tree.configure(yscrollcommand=prop_vsb.set)
                prop_vsb.pack(side="right", fill="y")
                prop_tree.pack(fill="both", expand=True)

                if prop_keys:
                    for k in sorted(prop_keys, key=lambda s: s.lower()):
                        v = props.get(k, None)
                        try:
                            display_v = "" if v is None else (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
                        except Exception:
                            display_v = str(v)
                        prop_tree.insert("", "end", values=(k, display_v))
                else:
                    prop_tree.insert("", "end", values=("(none)", ""))

                btn_frame = ttk.Frame(self)
                btn_frame.pack(pady=6)
                ttk.Button(btn_frame, text="Close", command=self.destroy).pack()

        # Prepare data for tables: summary = all keys except 'properties'; prop_keys = keys inside properties
        summary = {k: v for k, v in info.items() if k != "properties"}
        props = info.get("properties", {})
        prop_keys = list(props.keys()) if isinstance(props, dict) else []

        viewer = PropertiesTables(self.root, f"Properties: {node_id}", summary, prop_keys)
        self.root.wait_window(viewer)

    # ---------- Search Property Window ----------
    def search_property(self):
        gui = self
        # Pop-up window for property search
        class SearchWindow(tk.Toplevel):
            def __init__(self, master, treeview):
                super().__init__(master)
                self.title("Search Property")
                self.geometry("460x360")
                self.resizable(False, False)
                self.treeview = treeview
                self.result_entries = []
                self.result_texts = []

                if gui.display_mode == "multi":
                    self.search_sources = [
                        (system_key, gui.multi_trees[system_key]["tree"]) for system_key in sorted(gui.multi_trees.keys())
                    ]
                else:
                    self.search_sources = [("single", gui.tree_obj)] if gui.tree_obj else []

                frame = ttk.Frame(self)
                frame.pack(fill="both", expand=True, padx=10, pady=10)

                # Load node types
                nodes_types = ['any']
                if os.path.exists('required_properties.txt'):
                    with open('required_properties.txt', 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.split('#', 1)[0].strip()
                            if not line:
                                continue
                            try:
                                cls_key = line.split(':', 1)[0].strip()
                                if cls_key not in nodes_types:
                                    nodes_types.append(cls_key)
                            except Exception:
                                continue
                    for r in ['Processing_Step', 'Sample']:
                        if r in nodes_types:
                            nodes_types.remove(r)
                nodes_types = sorted(nodes_types)
                        

                # Load database_keys
                db_keys = []
                self.additional_keys = ['id', 'entry_created_date']
                if os.path.exists("database_keys.txt"):
                    with open("database_keys.txt", "r") as f:
                        db_keys = self.additional_keys + sorted(set(line.strip() for line in f if line.strip()))
                # Add 'id' and 'entry_created_date' as searchable property keys
                db_keys.append("<Custom key...>")
                
                def update_db_display_keys():
                    db_display_keys = self.additional_keys.copy()
                    if self.type_var.get() == "any":    # Show all keys
                        for node in nodes_types:
                            # if node == "any":
                            #     continue
                            prefix = node + "_"
                            for key in db_keys:
                                if key.startswith(prefix):
                                    trimmed_key = key[len(prefix):]
                                    if trimmed_key not in db_display_keys:
                                        db_display_keys.append(trimmed_key)
                    else:                           # Filter by selected node type
                        prefix = self.type_var.get() + "_"
                        for key in db_keys:
                            if key.startswith(prefix):
                                trimmed_key = key[len(prefix):]
                                if trimmed_key not in db_display_keys:
                                    db_display_keys.append(trimmed_key)
                    db_display_keys.append("<Custom key...>")
                    return db_display_keys
                    

                ttk.Label(frame, text="Node type:").grid(row=0, column=0, sticky="w")
                self.type_var = tk.StringVar(value='any')
                self.type_cb = ttk.Combobox(frame, values=nodes_types, textvariable=self.type_var, state="readonly", width=28)
                self.type_cb.grid(row=0, column=1, sticky="w")

                ttk.Label(frame, text="Property key:").grid(row=1, column=0, sticky="w")
                self.key_var = tk.StringVar()
                self.key_cb = ttk.Combobox(frame, values=update_db_display_keys(), textvariable=self.key_var, state="readonly", width=28)
                self.key_cb.grid(row=1, column=1, sticky="w")

                ttk.Label(frame, text="Property value (optional):").grid(row=2, column=0, sticky="w")
                self.val_var = tk.StringVar()
                self.val_entry = ttk.Entry(frame, textvariable=self.val_var, width=28)
                self.val_entry.grid(row=2, column=1, sticky="w")

                self.partial_var = tk.BooleanVar(value=False)
                self.partial_cb = ttk.Checkbutton(frame, text="Search partial match", variable=self.partial_var)
                self.partial_cb.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

                def on_key_select(_event):
                    # Handle custom key entry
                    if self.key_var.get() == "<Custom key...>":
                        new_key = simpledialog.askstring("Custom key", "Enter custom property key:", parent=self)
                        if new_key:
                            self.key_var.set(new_key)
                            if new_key not in db_keys and new_key != "":
                                db_keys.insert(-1, self.type_var.get() + "_" + new_key)
                                self.key_cb['values'] = update_db_display_keys()
                    # If node type changes, update available keys
                    elif _event.widget == self.type_cb:
                        self.key_cb['values'] = update_db_display_keys()
                        if self.key_cb.get() not in self.key_cb['values']:
                            self.key_var.set("")

                self.type_cb.bind("<<ComboboxSelected>>", on_key_select)
                self.key_cb.bind("<<ComboboxSelected>>", on_key_select)

                self.search_btn = ttk.Button(frame, text="Search", command=self.do_search)
                self.search_btn.grid(row=4, column=0, columnspan=2, pady=8)

                self.results_list = tk.Listbox(frame, height=10, width=48)
                self.results_list.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=4)
                self.results_list.bind("<Double-Button-1>", self.on_open_node)

                ttk.Button(frame, text="Close", command=self.destroy).grid(row=6, column=0, columnspan=2, pady=4)

                frame.rowconfigure(5, weight=1)
                frame.columnconfigure(1, weight=1)

            def _normalize_text(self, text, id_mode=False):
                import re

                normalized = str(text).lower()
                normalized = re.sub(r"[_-]+", " ", normalized)
                normalized = re.sub(r"\s+", " ", normalized).strip()
                if id_mode:
                    normalized = normalized.translate(str.maketrans({"b": "6", "6": "6", "e": "c", "c": "c"}))
                return normalized

            def _subsequence_match(self, query, target):
                query = query.replace(" ", "")
                target = target.replace(" ", "")
                if not query:
                    return True
                target_iter = iter(target)
                return all(ch in target_iter for ch in query)

            def _text_matches(self, query, target, mode, id_mode=False):
                if mode == "exact":
                    return self._normalize_text(query, id_mode) == self._normalize_text(target, id_mode)

                query_norm = self._normalize_text(query, id_mode)
                target_norm = self._normalize_text(target, id_mode)
                if query_norm in target_norm:
                    return True

                if mode == "subsequence":
                    return self._subsequence_match(query_norm, target_norm)

                return False

            def _matches_node(self, node, key_query, value_query, mode):
                obj = node.data.get("obj")
                if not obj:
                    return False, None, None

                props_raw = getattr(obj, "properties", {})
                if not isinstance(props_raw, dict):
                    return False, None, None

                props = dict(props_raw)
                props.update({attr_key: getattr(obj, attr_key, "") for attr_key in self.additional_keys if hasattr(obj, attr_key)})

                for prop_key, prop_value in props.items():
                    prop_key_text = str(prop_key)
                    prop_value_text = "" if prop_value is None else str(prop_value)
                    id_mode = prop_key_text.lower() == "id"

                    if mode == "exact":
                        key_ok = self._text_matches(key_query, prop_key_text, "exact", id_mode=False)
                        value_ok = True if value_query == "" else self._text_matches(value_query, prop_value_text, "exact", id_mode=id_mode)
                    else:
                        key_ok = self._text_matches(key_query, prop_key_text, mode, id_mode=False)
                        value_ok = True if value_query == "" else self._text_matches(value_query, prop_value_text, mode, id_mode=id_mode)

                    if key_ok and value_ok:
                        return True, prop_key_text, prop_value_text

                return False, None, None

            def _collect_matches(self, mode):
                matches = []
                seen_nodes = set()
                key_query = self.key_var.get().strip()
                value_query = self.val_var.get().strip()

                if not key_query:
                    return matches

                for system_key, tree in self.search_sources:
                    if not tree:
                        continue
                    for node in tree.all_nodes_itr():
                        if node.tag == "SYSTEM":
                            continue
                        if self.type_var.get() != "any" and node.tag != self.type_var.get():
                            continue

                        matched, prop_key, prop_value = self._matches_node(node, key_query, value_query, mode)
                        node_token = (system_key, node.identifier)
                        if matched and node_token not in seen_nodes:
                            matches.append((
                                system_key,
                                node.identifier,
                                node.tag,
                                getattr(node.data.get("obj"), "id", node.identifier),
                                prop_key,
                                prop_value,
                            ))
                            seen_nodes.add(node_token)

                return matches
                
            def do_search(self):
                self.results_list.delete(0, tk.END)
                self.search_btn.config(text="Searching...", state='disabled')
                self.result_entries = []
                self.result_texts = []

                try:
                    if not self.search_sources:
                        return

                    key = self.key_var.get().strip()
                    if not key:
                        return

                    node_type = self.type_var.get()
                    if not self.partial_var.get():
                        matches = self._collect_matches("exact")
                    else:
                        exact_matches = self._collect_matches("exact")
                        seen_nodes = {(system_key, node_id) for system_key, node_id, *_rest in exact_matches}
                        normalized_matches = self._collect_matches("substring")
                        matches = exact_matches[:]
                        for item in normalized_matches:
                            if (item[0], item[1]) not in seen_nodes:
                                matches.append(item)
                                seen_nodes.add((item[0], item[1]))

                        if not matches:
                            try_non_contiguous = messagebox.askyesno(
                                "No matches",
                                "No exact or normalized partial matches were found. Search for non-contiguous character matches?",
                                parent=self,
                            )
                            if try_non_contiguous:
                                matches = self._collect_matches("subsequence")

                    self.result_entries = [
                        {"system_key": system_key, "node_id": node_id}
                        for system_key, node_id, *_rest in matches
                    ]
                    if gui.display_mode == "multi":
                        self.result_texts = [
                            f"{node_tag} [{node_id_text}] ({os.path.basename(gui.multi_trees[system_key]['file'])}): {prop_key} = {prop_value}"
                            for system_key, node_id, node_tag, node_id_text, prop_key, prop_value in matches
                        ]
                    else:
                        self.result_texts = [
                            f"{node_tag} [{node_id_text}]: {prop_key} = {prop_value}"
                            for system_key, node_id, node_tag, node_id_text, prop_key, prop_value in matches
                        ]

                    for text in self.result_texts:
                        self.results_list.insert(tk.END, text)

                    if not self.result_entries:
                        self.results_list.insert(tk.END, "No matches found.")
                finally:
                    self.search_btn.config(text="Search", state='normal')

            def on_open_node(self, _event):
                sel = self.results_list.curselection()
                if not sel:
                    return
                idx = sel[0]
                if idx >= len(self.result_entries):
                    return
                entry = self.result_entries[idx]
                # Open this node in the treeview, closing all others
                self.open_and_focus_node(entry["system_key"], entry["node_id"])
                self.destroy()

            def open_and_focus_node(self, system_key, node_id):
                # Collapse all nodes
                for iid in self.treeview.get_children(""):
                    self.recursive_close(iid)
                if gui.display_mode == "multi":
                    info = gui.multi_trees.get(system_key)
                    if not info:
                        return
                    tree = info["tree"]
                    path = []
                    cur = node_id
                    while True:
                        node = tree.get_node(cur)
                        if node is None:
                            break
                        path.append(cur)
                        parent = tree.parent(cur)
                        if parent is None:
                            break
                        cur = parent.identifier
                    for nid in reversed(path):
                        iid = gui._multi_tree_iid(system_key, nid)
                        if not iid:
                            continue
                        try:
                            self.treeview.item(iid, open=True)
                        except Exception:
                            pass
                    target_iid = gui._multi_tree_iid(system_key, node_id)
                    if target_iid:
                        try:
                            self.treeview.selection_set(target_iid)
                            self.treeview.see(target_iid)
                        except Exception:
                            pass
                else:
                    tree = gui.tree_obj
                    if not tree:
                        return
                    path = []
                    cur = node_id
                    while True:
                        node = tree.get_node(cur)
                        if node is None:
                            break
                        path.append(cur)
                        parent = tree.parent(cur)
                        if parent is None:
                            break
                        cur = parent.identifier
                    for nid in reversed(path):
                        try:
                            self.treeview.item(nid, open=True)
                        except Exception:
                            pass
                    try:
                        self.treeview.selection_set(node_id)
                        self.treeview.see(node_id)
                    except Exception:
                        pass

            def recursive_close(self, iid):
                self.treeview.item(iid, open=False)
                for child in self.treeview.get_children(iid):
                    self.recursive_close(child)

        if self.display_mode == "multi":
            if not self.multi_trees:
                messagebox.showwarning("No Tree", "No tree loaded.")
                return
        else:
            if not self.tree_obj:
                messagebox.showwarning("No Tree", "No tree loaded.")
                return
        SearchWindow(self.root, self.treeview)

# ---------- Main Launch ----------
def launch_gui():
    root = tk.Tk()
    # action = show_discover_properties_window(root)
    # if action == "discover":
    #     discover_required_properties()
    _app = SampleTreeGUI(root)
    root.mainloop()


# if __name__ == "__main__":
#     launch_gui()