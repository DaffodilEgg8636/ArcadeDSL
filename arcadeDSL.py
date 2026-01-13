import re
import arcade
import arcade.gui
import ast
import os
import json



sample_code = """
    group(name="empty", anchor="center") {
        label(
            text="This DSL file is empty",
            x=50%w, y=50%h
        )
    }"""



def LoadDSLFiles(folder: str="dsl") -> dict:
    """
    Load all .dsl files from a folder into a dictionary.
    Returns {filename: file_contents}
    """
    global sample_code
    
    raw_code = {}
    folder = os.path.abspath(folder)  # absolute path

    if not os.path.exists(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    for filename in os.listdir(folder):
        if filename.endswith(".dsl"):
            key = os.path.splitext(filename)[0]  # remove extension
            with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
                value = f.read()
            if value:
                raw_code[key] = value
            else:
                raw_code[key] = sample_code

    return raw_code



def LoadDDSLFiles(folder: str="dsl") -> dict:
    """
    Load main.ddsl which contains the dynamic variables in JSON format.
    Returns a dict of variable_name: value
    """
    with open(f"{folder}/main.ddsl", "r") as f:
        vars = json.load(f)
    return vars



def ValidateDSLFiles(text: str) -> None:
    """
    Simple syntax check for balanced (), {}, []
    Raises SyntaxError if unmatched
    Args:
        text (str): DSL code to validate
    """
    stack = []
    for i, ch in enumerate(text):
        if ch in "({[":
            stack.append((ch, i))
        elif ch in ")}]":
            if not stack:
                raise SyntaxError(f"Unmatched '{ch}' at position {i}")
            opening, pos = stack.pop()
            if (opening, ch) not in [("(", ")"), ("{", "}"), ("[", "]")]:
                raise SyntaxError(f"Mismatched '{opening}' at {pos} and '{ch}' at {i}")

    if stack:
        raise SyntaxError(f"Unclosed '{stack[-1][0]}' at position {stack[-1][1]}")



def ParseRaw(code: str=sample_code, screen_width: int=800, screen_height: int=600) -> tuple:
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
    code = re.sub(r"//.*", "", code).strip()  # remove line comments
    styles = {}  # global style storage

    # ---------- Helper functions ----------
    def split_top_level_commas(s: str):
        """
        Split a string by commas, but ignore commas inside (), [], {} or quotes.
        Example: "x=1, y=(2,3)" -> ["x=1", "y=(2,3)"]
        """
        out, start = [], 0
        depth_paren = depth_brack = depth_brace = 0
        quote = None
        i = 0
        while i < len(s):
            ch = s[i]
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
                    out.append(s[start:i].strip())  # top-level comma found
                    start = i+1
            i += 1
        tail = s[start:].strip()
        if tail: out.append(tail)
        return out

    def split_kv(token: str):
        """
        Split a key=value pair, ignoring '=' inside quotes.
        """
        quote = None
        for i, ch in enumerate(token):
            if quote:
                if ch=="\\": continue
                if ch==quote: quote=None
            else:
                if ch in ("'", '"'): quote=ch
                elif ch=='=':
                    key = token[:i].strip()
                    val = token[i+1:].strip()
                    if not key: raise ValueError(f"Invalid argument: {token}")
                    return key, val
        raise ValueError(f"Missing '=' in token: {token}")

    def convert_value(value: str):
        """
        Convert raw string values to Python types:
        - %w / %h percentages -> pixel values
        - literals (int, float, str, list, dict, tuple, None, True, False)
        - fallback: keep as string
        """
        value = value.strip()
        # handle percentages relative to screen size
        if value.endswith("%w"): return screen_width * float(value[:-2])/100
        if value.endswith("%h"): return screen_height * float(value[:-2])/100
        try: return ast.literal_eval(value)  # try Python literal (safe eval)
        except:
            low = value.lower()
            if low=="true": return True
            if low=="false": return False
            if low=="none": return None
            if re.fullmatch(r"-?\d+", value): return int(value)
            if re.fullmatch(r"-?\d+\.\d+", value): return float(value)
            return value  # fallback: string

    def parse_props(raw_props: str):
        """
        Parse a raw props string like "x=10, text='Hi'" -> dict
        """
        if not raw_props.strip(): return {}
        props={}
        for token in split_top_level_commas(raw_props):
            if not token: continue
            k,v = split_kv(token)
            props[k]=convert_value(v)
        return props

    # ---------- Main block parser ----------

    def parse_block(block: str):
        """
        Parse a block of DSL code like:
        Button(x=10,y=20) { Label(text="Hello") }
        Returns a dict node with type/props/children
        """
        block = block.strip()
        m = re.match(r"^(\w+)\s*\((.*?)\)\s*(\{(.*)\})?$", block, re.DOTALL)
        if not m: raise ValueError(f"Invalid syntax: {block}")
        node_type, raw_props, _, raw_children = m.groups()
        props = parse_props(raw_props)

        # ---------- STYLE HANDLING ----------
        if node_type.lower() == "style":
            # Style(name="myStyle") { color=(255,0,0) }
            if "name" not in props:
                raise ValueError("Style() must have a 'name' parameter")
            style_name = props.pop("name")
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
            style_props.update(props)
            styles[style_name] = style_props
            return None  # style nodes don't become UI elements

        # ---------- CHILD NODE PARSING ----------
        children = []
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
                    if child: children.append(child)

        # ---------- STYLE APPLICATION ----------
        style_ref = props.pop("style_name", None)
        if style_ref and style_ref in styles:
            for k,v in styles[style_ref].items():
                props.setdefault(k,v)

        return {"type": node_type, "props": props, "children": children}

    # ---------- TOP LEVEL MULTI-BLOCK HANDLING ----------
    # Allows multiple root nodes, wrapped into a container if needed
    blocks = []
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
            blocks.append(block_text)

    # ---------- BUILD MAIN TREE ----------
    main_tree = None
    for block_text in blocks:
        parsed = parse_block(block_text)
        if parsed is not None:
            if main_tree is None:
                main_tree = parsed
            else:
                # if multiple non-style root blocks exist, wrap in container
                if main_tree.get("type") != "container":
                    main_tree = {
                        "type": "container", 
                        "props": {},
                        "children": [main_tree, parsed]
                    }
                else:
                    main_tree["children"].append(parsed)

    return main_tree, styles



def LinkDynamicVars(parsed_code: dict, variables: dict) -> None:
    """
    Link dynamic variables to DSL parsed code.
    - Stores dynamic_vars in parsed_code
    - Stores _dynamic_refs for future updates
    Args:
        parsed_code (dict): Parsed DSL tree
        variables (dict): Dynamic variables (from .ddsl file)
    """
    parsed_code["dynamic_vars"] = variables
    parsed_code["dynamic_refs"] = []

    def iterate_dict(parsed_code, d, v_key, v_value, variables):
        # Traverse nested dicts/lists
        for key, value in list(d.items()):
            if isinstance(value, dict):
                iterate_dict(parsed_code, d[key], v_key, v_value, variables)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        iterate_dict(parsed_code, item, v_key, v_value, variables)
            elif isinstance(value, str):
                if "<<" in value and ">>" in value:
                    var_name = value.replace("<<", "").replace(">>", "")
                    if v_key == var_name:
                        # Replace placeholder with actual variable value
                        d[key] = variables[v_key]
                        # Save reference for later dynamic updates
                        parsed_code["dynamic_refs"].append({
                            "target_dict": d,
                            "target_key": key,
                            "var_name": v_key
                        })

    # Iterate over all dynamic variables
    for key, value in variables.items():
        iterate_dict(parsed_code, parsed_code, key, value, variables)



def CreateUIObjs(tree: dict, styles: dict={}, parent_props={}, obj_list={}, root=None) -> dict:
    """
    Recursively create Arcade UI objects from a parsed DSL tree.
    Args:
        tree (dict): Parsed DSL tree
        styles (dict): Named styles from DSL parsing
    Args (recurrence):
        parent_props (dict): Inherited props from parent container
        obj_list (list): List of created UI objects
        root (dict): Root of the DSL tree (for dynamic vars)
    """
    # Start with inherited properties, then update with current node's props
    props = parent_props.copy()
    props.update(tree.get("props", {}))

    node_type = tree.get("type")
    children = tree.get("children", [])

    created_obj = None  # store the actual Arcade UI object
    if root is None:
        root = tree

    # ---------- CREATE SPECIFIC UI ELEMENTS ----------
    if node_type == "label":
        # Build a UILabel with all the provided properties
        label_kwargs = {
            "text": props.get("text", ""),
            "x": props.get("x", 0),
            "y": props.get("y", 0),
            "width": props.get("width", 0),
            "height": props.get("height", 0),
            "font_name": props.get("font_name", "Arial"),
            "font_size": props.get("font_size", 14),
            "text_color": props.get("text_color", (0,0,0,255)),
            "bold": props.get("bold", False),
            "italic": props.get("italic", False),
            "align": props.get("anchor", "center"),
            "multiline": props.get("multiline", False)
        }

        # Center adjustment if anchor=center
        if "anchor" in props:
            if props["anchor"] == "center":
                label_kwargs["x"] -= label_kwargs["width"] // 2
                label_kwargs["y"] -= label_kwargs["height"] // 2

        created_obj = arcade.gui.UILabel(**label_kwargs)

    elif node_type == "button":
        # Build a UIFlatButton
        button_kwargs = {
            "text": props.get("text", ""),
            "x": props.get("x", 0),
            "y": props.get("y", 0),
            "width": props.get("width", 100),
            "height": props.get("height", 100),
        }

        # Center adjustment
        if "anchor" in props:
            if props["anchor"] == "center":
                button_kwargs["x"] -= button_kwargs["width"] // 2
                button_kwargs["y"] -= button_kwargs["height"] // 2

        # ---------- STYLE HANDLING ----------
        style = props.get("style", None)
        if isinstance(style, dict):
            # state-based style dictionary
            has_states = any(key in ["normal", "hover", "press", "disabled"] for key in style.keys())
            if not has_states:
                # convert flat dict -> UIStyle for all states
                arcade_props = {}
                for key, value in style.items():
                    if key == "bg_color":
                        arcade_props["bg"] = value
                    elif key == "border_color":
                        arcade_props["border"] = value
                    else:
                        arcade_props[key] = value

                # Provide defaults
                arcade_props.setdefault("font_name", ("Arial",))
                arcade_props.setdefault("border_width", 2)

                # Filter only valid UIFlatButton.UIStyle keys
                valid_keys = {"font_size", "font_name", "font_color", "bg", "border", "border_width"}
                valid_props = {k:v for k,v in arcade_props.items() if k in valid_keys}

                # Create a UIStyle for all button states
                button_style = arcade.gui.UIFlatButton.UIStyle(**valid_props)
                button_kwargs["style"] = {state: button_style for state in ["normal","hover","press","disabled"]}
        elif isinstance(style, str):
            # Named style: look up in DSL styles
            if style in styles:
                named_style = styles[style]
                arcade_props = {}
                for key, value in named_style.items():
                    if key == "bg_color":
                        arcade_props["bg"] = value
                    elif key == "border_color":
                        arcade_props["border"] = value
                    else:
                        arcade_props[key] = value
                arcade_props.setdefault("font_name", ("Arial",))
                arcade_props.setdefault("border_width", 2)
                valid_keys = {"font_size", "font_name", "font_color", "bg", "border", "border_width"}
                valid_props = {k:v for k,v in arcade_props.items() if k in valid_keys}
                button_style = arcade.gui.UIFlatButton.UIStyle(**valid_props)
                button_kwargs["style"] = {state: button_style for state in ["normal","hover","press","disabled"]}

        # Default style if none provided
        else:
            normal_style = arcade.gui.UIFlatButton.UIStyle()
            button_kwargs["style"] = {state: normal_style for state in ["normal","hover","press","disabled"]}

        created_obj = arcade.gui.UIFlatButton(**button_kwargs)

    elif node_type == "input_text":
        # Build a UIInputText
        input_text_kwargs = {
            "text": props.get("text", ""),
            "x": props.get("x", 0),
            "y": props.get("y", 0),
            "width": props.get("width", 200),
            "height": props.get("height", 30),
            "font_name": props.get("font_name", "Arial"),
            "font_size": props.get("font_size", 14),
            "text_color": props.get("text_color", (0, 0, 0, 255)),
            "multiline": props.get("multiline", False)
        }

        if "anchor" in props:
            if props["anchor"] == "center":
                input_text_kwargs["x"] -= input_text_kwargs["width"] // 2
                input_text_kwargs["y"] -= input_text_kwargs["height"] // 2

        created_obj = arcade.gui.UIInputText(**input_text_kwargs)

    elif node_type == "text_area":
        # Build a UITextArea
        text_area_kwargs = {
            "text":props.get("text", ""),
            "x":props.get("x", 0),
            "y":props.get("y", 0),
            "width":props.get("width", 300),
            "height":props.get("height", 100),
            "font_name":props.get("font_name", "Arial"),
            "font_size":props.get("font_size", 12),
            "text_color":props.get("text_color", (0, 0, 0, 255)),
            "multiline":props.get("multiline", True),
            "scroll_speed":props.get("scroll_speed", 10.0)
        }

        if "anchor" in props:
            if props["anchor"] == "center":
                text_area_kwargs["x"] -= text_area_kwargs["width"] // 2
                text_area_kwargs["y"] -= text_area_kwargs["height"] // 2

        created_obj = arcade.gui.UITextArea(**text_area_kwargs)

    elif node_type == "space":
        # Invisible spacing widget
        space_kwargs = {
            "x":props.get("x", 0),
            "y":props.get("y", 0),
            "width":props.get("width", 100),
            "height":props.get("height", 100),
            "color":props.get("color", (0, 0, 0, 0))
        }

        if "anchor" in props:
            if props["anchor"] == "center":
                space_kwargs["x"] -= space_kwargs["width"] // 2
                space_kwargs["y"] -= space_kwargs["height"] // 2

        created_obj = arcade.gui.UISpace(**space_kwargs)

    elif node_type == "dummy":
        # Placeholder/dummy widget
        dummy_kwargs = {
            "x":props.get("x", 0),
            "y":props.get("y", 0),
            "width":props.get("width", 100),
            "height":props.get("height", 100),
            "color":props.get("color", (255, 0, 0))
        }
        created_obj = arcade.gui.UIDummy(**dummy_kwargs)

    elif node_type == "sprite_widget":
        # Sprite container widget
        sprite_widget_kwargs = {
            "sprite":props.get("sprite"),
            "x":props.get("x", 0),
            "y":props.get("y", 0),
            "width":props.get("width", 64),
            "height":props.get("height", 64)
        }
        created_obj = arcade.gui.UISpriteWidget(**sprite_widget_kwargs)

    elif node_type in ["group", "box_layout", "anchor_layout", "container"]:
        # Container nodes: only pass props to children; no direct object
        pass
    else:
        raise ValueError(f"Unknown UI element type: {node_type}")

    # ---------- DYNAMIC VARIABLE REFS ----------
    obj_list[-1] = root["dynamic_refs"]
    obj_list[-2] = root["dynamic_vars"]
    # Update dynamic reference to point to actual UI object
    for ref in obj_list[-1]:
        if ref["target_dict"] == tree["props"]:
            ref["target_dict"] = created_obj

    # Store created object in obj_list with name/tags
    if created_obj:
        obj_list[len(obj_list)-2] = [created_obj, props.get("name", ""), props.get("tags", [])]

    # ---------- RECURSIVE CHILD CREATION ----------
    for child in children:
        CreateUIObjs(tree=child, obj_list=obj_list, styles=styles, parent_props=props, root=root)

    return obj_list



def UpdateVars(data: dict) -> None:
    """
    Updates all UI objects that have dynamic variables.
    Called every frame or when variables change.
    Arguments:
        data (dict): List of UI objects with dynamic references (only one screen)
    """
    for ref in data[-1]:
        setattr(ref["target_dict"], ref["target_key"], data[-2][ref["var_name"]])



def InitializeUI(path: str="dsl", window: arcade.Window=None) -> dict:
    """
    Initialize the UI system with DSL files.
    Returns a dictionary of UI objects by DSL file.
    Args:
        path (str): Path to DSL files folder
        window (arcade.Window): Arcade window instance
    """
    # Load DSL files and dynamic variables
    vars = LoadDDSLFiles(path)
    raw_code = LoadDSLFiles(path)

    UIScreens = {}
    # Loop through each DSL file
    for key, value in raw_code.items():
        # Parse DSL code
        ValidateDSLFiles(value)  # Ensure DSL syntax is correct
        parsed_code, styles = ParseRaw(value, window.width, window.height)

        # Link dynamic variables
        LinkDynamicVars(parsed_code, vars)

        # Create UI objects from parsed DSL
        UIObjs = CreateUIObjs(tree=parsed_code, styles=styles)
        UIScreens[key] = UIObjs

    return UIScreens


