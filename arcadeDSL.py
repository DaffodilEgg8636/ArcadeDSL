import re
import arcade
import arcade.gui
import ast
import os
import json
import traceback



# NAMING CONVENTION (quick guide)
#
# ARGUMENTS (function parameters):
#   LIKE_THAT       → inputs from the function
#
# GLOBAL VARIABLES:
#   LikeThat        → mutable (dicts, lists, functions, etc.)
#   likeThat        → non-mutable (str, int, foat, tuple, etc.)
#
# LOCAL VARIABLES:
#   _like_that      → mutable 
#   like_that       → non-mutable 



sampleCode = """
    group(name="empty", anchor="center") {
        label(
            text="This DSL file is empty",
            x=50%w, y=50%h
        )
    }"""



def LoadDSLFiles(FOLDER: str="dsl") -> dict:
    """
    Load all .dsl files from a folder into a dictionary.
    Returns {filename: file_contents}
    """
    try:
        _raw_code = {}
        FOLDER = os.path.abspath(FOLDER)  # absolute path
    
        if not os.path.exists(FOLDER):
            raise FileNotFoundError(f"Folder not found: {FOLDER}")
    
        for filename in os.listdir(FOLDER):
            if filename.endswith(".dsl"):
                key = os.path.splitext(filename)[0]  # remove extension
                with open(os.path.join(FOLDER, filename), "r", encoding="utf-8") as f:
                    value = f.read()
                if value:
                    _raw_code[key] = value
                else:
                    _raw_code[key] = sampleCode
    
        return _raw_code

    except Exception:
        traceback.print_exc()
        return {}



def LoadDDSLFiles(FOLDER: str="dsl") -> dict:
    """
    Load main.ddsl which contains the dynamic variables in JSON format.
    Returns a dict of variable_name: value
    """
    try:
        with open(f"{FOLDER}/main.ddsl", "r") as f:
            _vars = json.load(f)
        return _vars

    except Exception:
        traceback.print_exc()
        return {}



def ValidateDSLFiles(TEXT: str) -> None:
    """
    Simple syntax check for balanced (), {}, []
    Raises SyntaxError if unmatched
    Args:
        text (str): DSL code to validate
    """
    try:
        _stack = []
        for i, ch in enumerate(TEXT):
            if ch in "({[":
                _stack.append((ch, i))
            elif ch in ")}]":
                if not _stack:
                    raise SyntaxError(f"Unmatched '{ch}' at position {i}")
                opening, pos = _stack.pop()
                if (opening, ch) not in [("(", ")"), ("{", "}"), ("[", "]")]:
                    raise SyntaxError(f"Mismatched '{opening}' at {pos} and '{ch}' at {i}")
    
        if _stack:
            raise SyntaxError(f"Unclosed '{_stack[-1][0]}' at position {_stack[-1][1]}")

    except Exception:
        traceback.print_exc()



def ParseRaw(CODE: str=sampleCode, SCREEN_WIDTH: int=800, SCREEN_HEIGHT: int=600) -> tuple:
    """
    Parse DSL code with support for:
    - UI elements (buttons, labels, groups)
    - Percentages (%w/%h)
    - style() blocks with reusable named styles
    Args:
        code (str): DSL code to parse
        screen_width (int): Screen width for percentage calculations
        screen_height (int): Screen height for percentage calculations
    Returns:
        parsed_tree (dict): Parsed DSL tree
        styles (dict): Named styles from DSL
    """
    try:
        code = re.sub(r"//.*", "", CODE).strip()  # remove line comments
        _styles = {}  # global style storage
    
        # ---------- Helper functions ----------
        def split_top_level_commas(S: str):
            """
            Split a string by commas, but ignore commas inside (), [], {} or quotes.
            Example: "x=1, y=(2,3)" -> ["x=1", "y=(2,3)"]
            """
            _out, start = [], 0
            depth_paren = depth_brack = depth_brace = 0
            quote = None
            i = 0
            while i < len(S):
                ch = S[i]
                if quote:
                    if ch == "\\": i += 2; continue  # skip escaped chars
                    if ch == quote: quote = None    # close quote
                else:
                    if ch in ("'", '"'): quote = ch
                    elif ch == '(': depth_paren += 1
                    elif ch == ')': depth_paren -= 1
                    elif ch == '[': depth_brack += 1
                    elif ch == ']': depth_brack -= 1
                    elif ch == '{': depth_brace += 1
                    elif ch == '}': depth_brace -= 1
                    elif ch == ',' and depth_paren==depth_brack==depth_brace==0:
                        _out.append(S[start:i].strip())  # top-level comma found
                        start = i+1
                i += 1
            tail = S[start:].strip()
            if tail: _out.append(tail)
            return _out
    
        def split_kv(TOKEN: str):
            """
            Split a key=value pair, ignoring '=' inside quotes.
            """
            quote = None
            for i, ch in enumerate(TOKEN):
                if quote:
                    if ch=="\\": continue
                    if ch==quote: quote=None
                else:
                    if ch in ("'", '"'): quote=ch
                    elif ch=='=':
                        key = TOKEN[:i].strip()
                        val = TOKEN[i+1:].strip()
                        if not key: raise ValueError(f"Invalid argument: {TOKEN}")
                        return key, val
            raise ValueError(f"Missing '=' in token: {TOKEN}")
    
        def convert_value(VALUE: str):
            """
            Convert raw string values to Python types:
            - %w / %h percentages -> pixel values
            - literals (int, float, str, list, dict, tuple, None, True, False)
            - fallback: keep as string
            """
            value = VALUE.strip()
            # handle percentages relative to screen size
            if value.endswith("%w"): return SCREEN_WIDTH * float(value[:-2])/100
            if value.endswith("%h"): return SCREEN_HEIGHT * float(value[:-2])/100
            try: return ast.literal_eval(value)  # try Python literal (safe eval)
            except:
                low = value.lower()
                if low=="true": return True
                if low=="false": return False
                if low=="none": return None
                if re.fullmatch(r"-?\d+", value): return int(value)
                if re.fullmatch(r"-?\d+\.\d+", value): return float(value)
                return value  # fallback: string
    
        def parse_props(RAW_PROPS: str):
            """
            Parse a raw props string like "x=10, text='Hi'" -> dict
            """
            if not RAW_PROPS.strip(): return {}
            _props={}
            for token in split_top_level_commas(RAW_PROPS):
                if not token: continue
                k,v = split_kv(token)
                _props[k]=convert_value(v)
            return _props
    
        # ---------- Main block parser ----------
    
        def parse_block(BLOCK: str):
            """
            Parse a block of DSL code like:
            button(x=10,y=20) { label(text="Hello") }
            Returns a dict node with type/props/children
            """
            block = BLOCK.strip()
            m = re.match(r"^(\w+)\s*\((.*?)\)\s*(\{(.*)\})?$", block, re.DOTALL)
            if not m: raise ValueError(f"Invalid syntax: {block}")
            node_type, raw_props, _, raw_children = m.groups()
            _props = parse_props(raw_props)
    
            # ---------- STYLE HANDLING ----------
            if node_type.lower() == "style":
                # Style(name="myStyle") { color=(255,0,0) }
                if "name" not in _props:
                    raise ValueError("style() must have a 'name' parameter")
                style_name = _props.pop("name")
                style_props = {}
                if raw_children:
                    # parse child lines as style properties
                    for line in raw_children.strip().splitlines():
                        line = line.strip()
                        if not line or line.startswith("//") or line.startswith("}") or line.startswith("{"): 
                            continue
                        if '=' not in line:
                            continue
                        key, value = line.split('=', 1)
                        style_props[key.strip()] = convert_value(value.strip())
                style_props.update(_props)
                _styles[style_name] = style_props
                return None  # style nodes don't become UI elements
    
            # ---------- CHILD NODE PARSING ----------
            _children = []
            if raw_children:
                # manually parse nested children
                s = raw_children.strip()
                i=0
                while i < len(s):
                    while i<len(s) and s[i].isspace(): i+=1
                    if i>=len(s): break
                    start=i
                    while i<len(s) and (s[i].isalnum() or s[i]=='_'): i+=1
                    while i<len(s) and s[i].isspace(): i+=1
                    if i>=len(s) or s[i]!='(': raise ValueError(f"Expected '(' after child near: {s[i:i+20]!r}")
                    # find matching parenthesis + braces
                    depth=0; quote=None
                    while i<len(s):
                        ch=s[i]
                        if quote:
                            if ch=="\\": i+=2; continue
                            if ch==quote: quote=None
                        else:
                            if ch in ("'", '"'): quote=ch
                            elif ch=='(': depth+=1
                            elif ch==')': depth-=1
                            if depth==0: i+=1; break
                        i+=1
                    while i<len(s) and s[i].isspace(): i+=1
                    if i<len(s) and s[i]=='{':
                        depth=0; quote=None
                        while i<len(s):
                            ch=s[i]
                            if quote:
                                if ch=="\\": i+=2; continue
                                if ch==quote: quote=None
                            else:
                                if ch in ("'", '"'): quote=ch
                                elif ch=='{': depth+=1
                                elif ch=='}': depth-=1
                                if depth==0: i+=1; break
                            i+=1
                    child_block = s[start:i].strip()
                    if child_block:
                        child = parse_block(child_block)
                        if child: _children.append(child)
    
            # ---------- STYLE APPLICATION ----------
            style_ref = _props.pop("style_name", None)
            if style_ref and style_ref in _styles:
                for k,v in _styles[style_ref].items():
                    _props.setdefault(k,v)
    
            return {"type": node_type, "props": _props, "children": _children}
    
        # ---------- TOP LEVEL MULTI-BLOCK HANDLING ----------
        # Allows multiple root nodes, wrapped into a container if needed
        _blocks = []
        i = 0
        code = code.strip()
    
        while i < len(code):
            # find block start and end manually (similar logic as child parsing)
            while i < len(code) and code[i].isspace(): i += 1
            if i >= len(code): break
    
            start = i
            while i < len(code) and (code[i].isalnum() or code[i] == '_'): i += 1
            while i < len(code) and code[i].isspace(): i += 1
            if i >= len(code) or code[i] != '(': break
    
            depth = 0
            quote = None
            paren_depth = 0
            while i < len(code):
                ch = code[i]
                if quote:
                    if ch == "\\" and i + 1 < len(code):
                        i += 2
                        continue
                    if ch == quote:
                        quote = None
                else:
                    if ch in ("'", '"'):
                        quote = ch
                    elif ch == '(':
                        paren_depth += 1
                    elif ch == ')':
                        paren_depth -= 1
                    elif ch == '{' and paren_depth == 0:
                        depth += 1
                    elif ch == '}' and paren_depth == 0:
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                i += 1
    
            block_text = code[start:i].strip()
            if block_text:
                _blocks.append(block_text)
    
        # ---------- BUILD MAIN TREE ----------
        _main_tree = None
        for block_text in _blocks:
            _parsed = parse_block(block_text)
            if _parsed is not None:
                if _main_tree is None:
                    _main_tree = _parsed
                else:
                    # if multiple non-style root blocks exist, wrap in container
                    if _main_tree.get("type") != "container":
                        _main_tree = {
                            "type": "container", 
                            "props": {},
                            "children": [_main_tree, _parsed]
                        }
                    else:
                        _main_tree["children"].append(_parsed)
    
        return _main_tree, _styles

    except Exception:
        traceback.print_exc()
        return {}, {}



def LinkDynamicVars(PARSED_CODE: dict, VARIABLES: dict) -> None:
    """
    Link dynamic variables to DSL parsed code.
    - Stores dynamic_vars in parsed_code
    - Stores dynamic_refs for future updates
    Args:
        parsed_code (dict): Parsed DSL tree
        variables (dict): Dynamic variables (from .ddsl file)
    """
    try:
        PARSED_CODE["dynamic_vars"] = VARIABLES
        PARSED_CODE["dynamic_refs"] = []
    
        def iterate_dict(PARSED_CODE, D, V_KEY, V_VALUE, VARIABLES):
            # Traverse nested dicts/lists
            for key, value in list(D.items()):
                if isinstance(value, dict):
                    iterate_dict(PARSED_CODE, D[key], V_KEY, V_VALUE, VARIABLES)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            iterate_dict(PARSED_CODE, item, V_KEY, V_VALUE, VARIABLES)
                elif isinstance(value, str):
                    if "<<" in value and ">>" in value:
                        var_name = value.replace("<<", "").replace(">>", "")
                        if V_KEY == var_name:
                            # Replace placeholder with actual variable value
                            D[key] = None
                            # Save reference for later dynamic updates
                            PARSED_CODE["dynamic_refs"].append({
                                "target_dict": D,
                                "target_key": key,
                                "var_name": V_KEY
                            })
    
        # Iterate over all dynamic variables
        for key, value in VARIABLES.items():
            iterate_dict(PARSED_CODE, PARSED_CODE, key, value, VARIABLES)

    except Exception:
        traceback.print_exc()



def CreateUIObjs(TREE: dict, STYLES: dict={}, PARENT_PROPS={}, OBJ_LIST={}, ROOT=None, GROUP_DYNAMIC_REFS=None) -> dict:
    """
    Recursively create Arcade UI objects from a parsed DSL tree.
    Args:
        tree (dict): Parsed DSL tree
        styles (dict): Named styles from DSL parsing
    Args (recurrence):
        parent_props (dict): Inherited props from parent container
        obj_list (list): List of created UI objects
        root (dict): Root of the DSL tree (for dynamic vars)
        group_dynamic_refs (list): Dynamic refs for group children
    """
    try:
        # Start with inherited properties, then update with current node's props
        _props = PARENT_PROPS.copy()
        _props.update(TREE.get("props", {}))
    
        node_type = TREE.get("type")
        _children = TREE.get("children", [])
    
        _created_obj = None  # store the actual Arcade UI object
        if ROOT is None:
            ROOT = TREE
    
        if GROUP_DYNAMIC_REFS is None:
            GROUP_DYNAMIC_REFS = []
    
        # ---------- CREATE SPECIFIC UI ELEMENTS ----------
        if node_type == "label":
            # Build a UILabel with all the provided properties
            _label_kwargs = {
                "text": _props.get("text", "") or "Empty",
                "x": _props.get("x", 0) or 0,
                "y": _props.get("y", 0) or 0,
                "width": _props.get("width", 0) or 0,
                "height": _props.get("height", 0) or 0,
                "font_name": _props.get("font_name", "Arial") or "Arial",
                "font_size": _props.get("font_size", 14) or 14,
                "text_color": _props.get("text_color", (0,0,0,255)) or (0,0,0,255),
                "bold": _props.get("bold", False) or False,
                "italic": _props.get("italic", False) or False,
                "align": _props.get("anchor", "center") or "center",
                "multiline": _props.get("multiline", False) or False
            }
    
            # Center adjustment if anchor=center
            if "anchor" in _props:
                if _props["anchor"] == "center":
                    _label_kwargs["x"] -= _label_kwargs["width"] // 2
                    _label_kwargs["y"] -= _label_kwargs["height"] // 2
    
            _created_obj = arcade.gui.UILabel(**_label_kwargs)
    
        elif node_type == "button":
            # Build a UIFlatButton
            _button_kwargs = {
                "text": _props.get("text", "") or "Empty",
                "x": _props.get("x", 0) or 0,
                "y": _props.get("y", 0) or 0,
                "width": _props.get("width", 100) or 0,
                "height": _props.get("height", 100) or 0,
            }
    
            # Center adjustment
            if "anchor" in _props:
                if _props["anchor"] == "center":
                    _button_kwargs["x"] -= _button_kwargs["width"] // 2
                    _button_kwargs["y"] -= _button_kwargs["height"] // 2
    
            # ---------- STYLE HANDLING ----------
            style = _props.get("style", None)
            if isinstance(style, dict):
                # state-based style dictionary
                has_states = any(key in ["normal", "hover", "press", "disabled"] for key in style.keys())
                if not has_states:
                    # convert flat dict -> UIStyle for all states
                    _arcade_props = {}
                    for key, value in style.items():
                        if key == "bg_color":
                            _arcade_props["bg"] = value
                        elif key == "border_color":
                            _arcade_props["border"] = value
                        else:
                            _arcade_props[key] = value

                    # Provide defaults
                    _arcade_props.setdefault("font_name", ("Arial",))
                    _arcade_props.setdefault("border_width", 2)
    
                    # Filter only valid UIFlatButton.UIStyle keys
                    _valid_keys = {"font_size", "font_name", "font_color", "bg", "border", "border_width"}
                    _valid_props = {k:v for k,v in arcade_props.items() if k in valid_keys}
    
                    # Create a UIStyle for all button states
                    _button_style = arcade.gui.UIFlatButton.UIStyle(**valid_props)
                    _button_kwargs["style"] = {state: _button_style for state in ["normal","hover","press","disabled"]}
            elif isinstance(style, str):
                # Named style: look up in DSL styles
                if style in STYLES:
                    _named_style = STYLES[style]
                    _arcade_props = {}
                    for key, value in _named_style.items():
                        if key == "bg_color":
                            _arcade_props["bg"] = value
                        elif key == "border_color":
                            _arcade_props["border"] = value
                        else:
                            _arcade_props[key] = value
                    _arcade_props.setdefault("font_name", ("Arial",))
                    _arcade_props.setdefault("border_width", 2)
                    _valid_keys = {"font_size", "font_name", "font_color", "bg", "border", "border_width"}
                    _valid_props = {k:v for k,v in _arcade_props.items() if k in _valid_keys}
                    _button_style = arcade.gui.UIFlatButton.UIStyle(**_valid_props)
                    _button_kwargs["style"] = {state: _button_style for state in ["normal","hover","press","disabled"]}
    
            # Default style if none provided
            else:
                _normal_style = arcade.gui.UIFlatButton.UIStyle()
                _button_kwargs["style"] = {state: _normal_style for state in ["normal","hover","press","disabled"]}
    
            _created_obj = arcade.gui.UIFlatButton(**_button_kwargs)
    
        elif node_type == "input_text":
            # Build a UIInputText
            _input_text_kwargs = {
                "text": _props.get("text", "") or "Empty",
                "x": _props.get("x", 0) or 0,
                "y": _props.get("y", 0) or 0,
                "width": _props.get("width", 200) or 0,
                "height": _props.get("height", 30) or 0,
                "font_name": _props.get("font_name", "Arial") or "Arial",
                "font_size": _props.get("font_size", 14) or 14,
                "text_color": _props.get("text_color", (0, 0, 0, 255)) or (0,0,0,255),
                "multiline": _props.get("multiline", False) or False
            }
    
            if "anchor" in _props:
                if _props["anchor"] == "center":
                    _input_text_kwargs["x"] -= _input_text_kwargs["width"] // 2
                    _input_text_kwargs["y"] -= _input_text_kwargs["height"] // 2
    
            _created_obj = arcade.gui.UIInputText(**_input_text_kwargs)
    
        elif node_type == "text_area":
            # Build a UITextArea
            _text_area_kwargs = {
                "text": _props.get("text", "") or "Empty",
                "x": _props.get("x", 0) or 0,
                "y": _props.get("y", 0) or 0,
                "width": _props.get("width", 200) or 0,
                "height": _props.get("height", 30) or 0,
                "font_name": _props.get("font_name", "Arial") or "Arial",
                "font_size": _props.get("font_size", 14) or 14,
                "text_color": _props.get("text_color", (0, 0, 0, 255)) or (0,0,0,255),
                "multiline": _props.get("multiline", False) or False,
                "scroll_speed":_props.get("scroll_speed", 10.0)
            }
    
            if "anchor" in _props:
                if _props["anchor"] == "center":
                    _text_area_kwargs["x"] -= _text_area_kwargs["width"] // 2
                    _text_area_kwargs["y"] -= _text_area_kwargs["height"] // 2
    
            _created_obj = arcade.gui.UITextArea(**_text_area_kwargs)
    
        elif node_type == "space":
            # Invisible spacing widget
            _space_kwargs = {
                "x":_props.get("x", 0) or 0,
                "y":_props.get("y", 0) or 0,
                "width":_props.get("width", 100) or 0,
                "height":_props.get("height", 100) or 0,
                "color":_props.get("color", (0, 0, 0, 0)) or (0, 0, 0, 0)
            }
    
            if "anchor" in _props:
                if _props["anchor"] == "center":
                    _space_kwargs["x"] -= _space_kwargs["width"] // 2
                    _space_kwargs["y"] -= _space_kwargs["height"] // 2
    
            _created_obj = arcade.gui.UISpace(**_space_kwargs)
    
        elif node_type == "dummy":
            # Placeholder/dummy widget
            _dummy_kwargs = {
                "x":_props.get("x", 0) or 0,
                "y":_props.get("y", 0) or 0,
                "width":_props.get("width", 100) or 0,
                "height":_props.get("height", 100) or 0,
                "color":_props.get("color", (0, 0, 0, 0)) or (0, 0, 0, 0)
            }
            _created_obj = arcade.gui.UIDummy(**_dummy_kwargs)
    
        elif node_type == "sprite_widget":
            # Sprite container widget
            _sprite_widget_kwargs = {
                "sprite":_props.get("sprite"),
                "x":_props.get("x", 0) or 0,
                "y":_props.get("y", 0) or 0,
                "width":_props.get("width", 64) or 0,
                "height":_props.get("height", 64) or 0
            }
            _created_obj = arcade.gui.UISpriteWidget(**_sprite_widget_kwargs)
    
        elif node_type in ["group", "box_layout", "anchor_layout", "container"]:
            # Container nodes: only pass props to children; no direct object
            pass
        else:
            raise ValueError(f"Unknown UI element type: {node_type}")
    
    
        # Store created object in obj_list with name/tags
        if _created_obj:
            OBJ_LIST[len(OBJ_LIST)-2] = [_created_obj, _props.get("name", ""), _props.get("tags", [])]
    
        
        # ---------- DYNAMIC VARIABLE REFS ----------
        if ROOT == TREE:
            OBJ_LIST[-1] = ROOT["dynamic_refs"]
            OBJ_LIST[-2] = ROOT["dynamic_vars"]
    
        # Update dynamic reference to point to actual UI object
        for _ref in OBJ_LIST[-1]:
            if _ref["target_dict"] == TREE["props"]:
                if node_type == "group":
                    temp = 0
                    for _group_ref in GROUP_DYNAMIC_REFS:
                        if _group_ref["target_key"] == _ref["target_key"]:
                            _group_ref["var_name"] = _ref["var_name"]
                            temp = 1
                    if temp == 0:
                        GROUP_DYNAMIC_REFS.append({
                            "target_dict": _ref["target_dict"],
                            "target_key": _ref["target_key"],
                            "var_name": _ref["var_name"]
                        })
                else:
                    if _ref["target_key"] == "name" or _ref["target_key"] == "tags":
                        _ref["target_dict"] = OBJ_LIST[len(OBJ_LIST)-3]
                    else:
                        _ref["target_dict"] = _created_obj
    
        # Apply dynamic references to group children
        if node_type != "group":
            for _ref in GROUP_DYNAMIC_REFS:
                if not _props.get(_ref["target_key"], None):
                    if _ref["target_key"] == "name" or _ref["target_key"] == "tags":
                        child_ref = {
                            "target_dict": OBJ_LIST[len(OBJ_LIST)-3],
                            "target_key": 1 if _ref["target_key"] == "name" else 2,
                            "var_name": _ref["var_name"]
                        }
                        OBJ_LIST[-1].append(child_ref)
                    else:
                        child_ref = {
                            "target_dict": _created_obj,
                            "target_key": _ref["target_key"],
                            "var_name": _ref["var_name"]
                        }
                        OBJ_LIST[-1].append(child_ref)
    
        # After processing group and its children, remove group's own refs
        if node_type == "group":
            OBJ_LIST[-1] = [_ref for _ref in OBJ_LIST[-1] 
                            if _ref["target_dict"] != TREE["props"]]
                    
    
        # ---------- RECURSIVE CHILD CREATION ----------
        for child in _children:
            CreateUIObjs(TREE=child, OBJ_LIST=OBJ_LIST, STYLES=STYLES, PARENT_PROPS=_props, ROOT=ROOT, GROUP_DYNAMIC_REFS=GROUP_DYNAMIC_REFS)
    
        return OBJ_LIST

    except Exception:
        traceback.print_exc()
        return {}



def UpdateVars(DATA: dict) -> None:
    """
    Updates all UI objects that have dynamic variables.
    Called every frame or when variables change.
    Arguments:
        data (dict): List of UI objects with dynamic references (only one screen)
    """
    try:
        for _ref in DATA[-1]:
            if isinstance(_ref["target_dict"], dict) or isinstance(_ref["target_dict"], list):
                _ref["target_dict"][_ref["target_key"]] = DATA[-2][_ref["var_name"]]
            else:
                setattr(_ref["target_dict"], _ref["target_key"], DATA[-2][_ref["var_name"]])

    except Exception:
        traceback.print_exc()



def InitializeUI(PATH: str="dsl", WINDOW: arcade.Window=arcade.Window(800, 600)) -> dict:
    """
    Initialize the UI system with DSL files.
    Returns a dictionary of UI objects by DSL file.
    Args:
        path (str): Path to DSL files folder
        window (arcade.Window): Arcade window instance
    """
    try:
        # Load DSL files and dynamic variables
        _vars = LoadDDSLFiles(PATH)
        _raw_code = LoadDSLFiles(PATH)
    
        _ui_screens = {}
        # Loop through each DSL file
        for key, _value in _raw_code.items():
            # Parse DSL code
            ValidateDSLFiles(_value)  # Ensure DSL syntax is correct
            _parsed_code, _styles = ParseRaw(_value, WINDOW.width, WINDOW.height)
    
            # Link dynamic variables
            LinkDynamicVars(_parsed_code, _vars)
    
            # Create UI objects from parsed DSL
            _ui_objs = CreateUIObjs(TREE=_parsed_code, STYLES=_styles)
            UpdateVars(_ui_objs)
            _ui_screens[key] = _ui_objs
    
        return _ui_screens

    except Exception:
        traceback.print_exc()
        return {}



def CreateManagers(UI_SCREENS: dict, WINDOW=None) -> dict:
    """
    Create UI managers for each screen.
    Args:
        UIScreens (dict): Dictionary of UI objects by DSL file
        window (arcade.Window): Arcade window instance
    """
    return {}
