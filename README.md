# Arcade DSL UI Builder

## This branch contains currently developped and not tested code. THIS README MIGHT NOT BE UP TO DATE

**Important**: This project is still under development and isn’t fully tested. I don’t recommend using this if you’re unexperienced. You will soon find a full documentation in this repository.

A powerful Domain-Specific Language (DSL) parser and UI builder for the Arcade game library. Create complex UI layouts declaratively with a simple, human-readable syntax.


## Features
- **Declarative UI Definition**: Define UI layouts using a simple, intuitive DSL syntax
- **Dynamic Variables**: Link UI elements to dynamic variables that can update in real-time
- **Named Button Styles**: Create reusable button style definitions and apply them across multiple elements
- **Responsive Design**: Support for percentage-based dimensions (`%w`, `%h`) relative to screen size
- **Multiple Layouts**: Support for multiple UI layouts loaded from separate `.dsl` files
- **Flexible Element Types**: Built-in support for buttons, labels, input fields, text areas, and more
- **Arcade Integration**: Seamlessly integrates with Arcade's UI system


## Requirements
- Python 3.7+
- `arcade` library (>=2.6.0)


## Installation
Project Structure
```
project/
├── dsl/                    # DSL files directory
│   ├── main.ddsl          # Dynamic variables (JSON format)
│   ├── menu.dsl           # Menu UI layout
│   ├── game.dsl           # In-game UI layout
│   └── ...
├── ui_builder.py          # This script
└── main.py               # Your main game file
```


## DSL Syntax Guide
### Basic Syntax
```
# Creation of a group to center all objects without rewriting the argument for every element
group(name="centered", anchor="center") {
    # Apply shared parameters to avoid rewriting them and apply button style
    group(name="tab_switch", bold=true, y=96%h, height=8%h, width=32%w, style="button") {
        # Creation of the objects using different arguments
        button(
            text="Programs",
            x=16%w,
            tags=["tab_switch", "programs"]
        )
        button(
            text="Servers",
            x=50%w,
            width=36%w,
            tags=["tab_switch", "servers"]
        )
        button(
            text="Account",
            x=84%w,
            style="disabled_button"
        )
    }
```

### Supported UI Elements

**Group**: (`group`) Sets parameters for all of its objects, takes any argument

**Label**: (`label`) Text label
- text : (str) Text of the label
- x : (int/double) X coordinate
- y : (int/double) Y coordinate
- width : (int/double) Width of the object (especially useful for filled backgrounds with height arg)
- height : (int/double) Height of the object
- font_name : (str) Name of the wanted font (note: it has to be installed in the system)
- font_size : (int/double) Size of the text (you can use dynamic screen values to make the text adaptable based on screen resolution)
- text_color : (tuple(4)) Takes (R,G,B,A), defines the color of the text
- bold : (bool) Sets bold text decoration
- italic : (bool) Sets italic text decoration
- anchor : (str) Takes “center“, […] ; sets up the alignment point of the object
- multiline : (bool) Enables/disables multiline text

**Button**: (`button`) Clickable button
- text : (str) Text of the button
- x : (int/double) X coordinate
- y : (int/double) Y coordinate
- width : Width of the object
- height : Height of the object
- anchor : (str) Takes “center“, […] ; sets up the alignment point of the object
- style : (str) Name of the style to apply

**Input Text**: (`input_text`) Text input field
- text : (str) Text of the label
- x : (int/double) X coordinate
- y : (int/double) Y coordinate
- width : (int/double) Width of the object
- height : (int/double) Height of the object
- font_name : (str) Name of the wanted font (note: it has to be installed in the system)
- font_size : (int/double) Size of the text (you can use dynamic screen values to make the text adaptable based on screen resolution)
- text_color : (tuple(4)) Takes (R,G,B,A), defines the color of the text
- anchor : (str) Takes “center“, […] ; sets up the alignment point of the object
- multiline : (bool) Enables/disables multiline text

**Text Area**: (`text_area`) Multiline text area
- text : (str) Text of the label
- x : (int/double) X coordinate
- y : (int/double) Y coordinate
- width : (int/double) Width of the object
- height : (int/double) Height of the object
- font_name : (str) Name of the wanted font (note: it has to be installed in the system)
- font_size : (int/double) Size of the text (you can use dynamic screen values to make the text adaptable based on screen resolution)
- text_color : (tuple(4)) Takes (R,G,B,A), defines the color of the text
- anchor : (str) Takes “center“, […] ; sets up the alignment point of the object
- multiline : (bool) Enables/disables multiline text
- scroll_speed : (int/double) Sets the scrolling coefficient

**Space**: (`space`) Invisible space widget
- x : (int/double) X coordinate
- y : (int/double) Y coordinate
- width : (int/double) Width of the object
- height : (int/double) Height of the object
- color : (tuple) Takes (R,G,B,A), sets up the color of the object
- anchor : (str) Takes “center“, […] ; sets up the alignment point of the object

**Dummy**: (`dummy`) Placeholder widget
- x : (int/double) X coordinate
- y : (int/double) Y coordinate
- width : (int/double) Width of the object
- height : (int/double) Height of the object
- color : (tuple) Takes (R,G,B,A), sets up the color of the object
- anchor : (str) Takes “center“, […] ; sets up the alignment point of the object

**Sprite Widget**: (`sprite_widget`) Sprite container widget
- sprite : […]
- x : (int/double) X coordinate
- y : (int/double) Y coordinate
- width : (int/double) Width of the object
- height : (int/double) Height of the object


### Dynamic Variables
Use `<<variable_name>>` syntax to link UI properties to dynamic variables:
```
# In your DSL file:
label(text="<<score>>", x=10, y=10)

# In main.ddsl file:
{"score": "0"}

# In your Python code:
variables = load_ddsl_files() # Loads the variables from main.ddsl (by default)
parsed_ui = set_dsl_keys(parsed_tree, variables)
``` 


### Named Styles
Define reusable button styles with the `style()` block. Takes `name` as only parameter:
```
style(name="primaryButton") {
    bg_color=(70, 70, 70, 255)
    border_color=(100, 100, 100, 255)
    font_size=16
    font_color=(255, 255, 255, 255)
}

# Apply the style
button(x=100, y=100, text="Start", style="primaryButton")
```


## Usage Example
1. Create DSL Files
dsl/menu.dsl:
```
style(name="primaryButton") {
    bg_color=(70, 70, 70, 255)
    border_color=(100, 100, 100, 255)
    font_size=16
}

style(name="titleText") {
    font_size=24
    font_color=(255, 255, 0, 255)
    bold=true
}

group(anchor="center") {
    label(text="My Awesome Game", 
           x=50%w, y=80%h, 
           font_size=24, 
           font_color=(255, 255, 0, 255), 
           bold=true)
    
    button(text="Start Game", 
           x=50%w, y=50%h, 
           width=200, height=50, 
           style="primaryButton")
    
    button(text="Options", 
           x="50%w", y="40%h", 
           width=200, height=50, 
           style_name="primaryButton")
    
    label(text="Score: <<current_score>>", 
           x=20, y=20)
}
```

dsl/main.ddsl (JSON format for dynamic variables):
```
{
    "current_score": "0",
    "player_health": "100",
    "game_time": "0"
}
```

2. Integrate with Your Game
**(Code generated by AI and not tested, do not copy or imitate it)**
```
import arcade
import arcade.gui
from ui_builder import *

class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(800, 600, "DSL UI Example")
        
        # Load all DSL files
        self.dsl_content = load_dsl_files("dsl")
        self.dynamic_vars = load_ddsl_files("dsl")
        
        # Parse and build UI
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()
        
        # Parse menu UI
        self.menu_tree, styles = interpret_ui(self.dsl_content["menu"])
        
        # Link dynamic variables
        set_dsl_keys(self.menu_tree, self.dynamic_vars)
        
        # Build UI objects
        self.ui_objects = {}
        build_ui_from_tree(self.menu_tree, self.ui_objects, styles)
        
        # Add to UI manager
        if self.menu_tree["type"] == "container":
            for child in self.menu_tree["children"]:
                if "ui_object" in child:
                    self.ui_manager.add(child["ui_object"])
    
    def on_draw(self):
        self.clear()
        self.ui_manager.draw()
    
    def update(self, delta_time):
        # Update dynamic variables
        self.dynamic_vars["game_time"] += delta_time
        
        # Refresh UI with updated values
        update_ui({"DSLRaw": {"menu": self.menu_tree}, "currentUI": "menu"})
    
    def on_mouse_press(self, x, y, button, modifiers):
        # Handle button clicks, etc.
        pass

def main():
    game = MyGame()
    game.run()

if __name__ == "__main__":
    main()
```


## Tips & Best Practices
Organize UI in Separate Files: Keep different screens (menu, game, settings) in separate .dsl files
Use Named Styles: Define common styles once and reuse them
Responsive Design: Use percentage values (%w, %h) for cross-resolution compatibility
Group Related Elements: Use Group blocks to organize related UI elements and avoid resetting parameters
Validate Early: Use validate_dsl() to catch syntax errors during development


## Error Handling
The parser includes comprehensive mostly partial error checking:
- Syntax errors (unbalanced brackets, missing parentheses)
- Invalid property assignments
- Missing style references
- File loading errors


## Contributing
To help me develop this project, please consider contacting me via Mail or Discord.
d70767176@gmail.com / @dafffod (I’ll respond probably faster on Discord)


## Support
For issues, questions, or feature requests:
- Review the DSL syntax guide (Coming soon)
- Open an issue on GitHub
