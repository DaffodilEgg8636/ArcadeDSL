import arcade
import arcadeDSL
import json


class LauncherView(arcade.View):
    """
    Main view for the launcher.
    Handles shared variables, dynamic UI, visuals, and input processing.
    """
    def __init__(self):
        super().__init__()

    # ---------- ARCADE VIEW EVENTS ----------
    def on_show_view(self):
        """Called when the view is shown"""
        self.clear()

    def on_draw(self):
        """Render visuals every frame"""
        pass

    def on_update(self, delta_time):
        """Update logic every frame"""
        pass

    def on_key_press(self, key, modifiers):
        """Handle key presses"""
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        """Handle mouse button presses"""
        pass

    def on_mouse_motion(self, x, y, dx, dy):
        """Handle mouse movement"""
        pass

    def get_process(self):
        """Return self for external reference"""
        return self


def LoadDSL(path: str = "dsl", resolution: tuple = (800, 600)) -> dict:
    """
    Loads and parses all DSL files using arcadeDSL.
    Also sets up dynamic variables for live updates.

    Args:
        shared (dict): A dictionary shared across processes for dynamic vars and UI objects

    Returns:
        dict: Dictionary of UI objects by DSL file
    """

    vars = arcadeDSL.LoadDDSLFiles(path)
    raw_ui = arcadeDSL.LoadDSLFiles(path)
    
    UIScreens = {}
    
    for key, value in raw_ui.items():
        arcadeDSL.ValidateDSLFiles(value)  # Ensure DSL syntax is correct
        parsed_code, styles = arcadeDSL.ParseRaw(value, resolution[0], resolution[1])

        # Link dynamic variables
        arcadeDSL.LinkDynamicVars(parsed_code, vars)
        
        # Create UI objects from parsed DSL
        UIObjs = arcadeDSL.CreateUIObjs(tree=parsed_code, styles=styles)
        UIScreens[key] = UIObjs

        with open("output.json", "w") as f:
            f.write(str(UIScreens))






        



window = arcade.Window(800, 600, "Arcade DSL Test")
view = LauncherView()
window.show_view(view)
LoadDSL()
arcade.run()
