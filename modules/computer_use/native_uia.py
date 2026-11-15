"""
Windows Native UI Automation & Accessibility Tree Inspector
Inspects native application controls (buttons, text fields, lists, dialogs)
using Windows UI Automation (IUIAutomation) and pywinauto.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("jarvis.computer_use.uia")

try:
    import uiautomation as auto
    UIA_AVAILABLE = True
except ImportError:
    UIA_AVAILABLE = False


class NativeUIAutomationEngine:
    """Interacts with native Windows applications via the accessibility tree."""

    def __init__(self):
        if UIA_AVAILABLE:
            auto.SetGlobalSearchTimeout(2.0)

    def is_available(self) -> bool:
        return UIA_AVAILABLE

    def inspect_active_window(self, max_depth: int = 3) -> Dict[str, Any]:
        """
        Inspects the foreground window and returns interactive accessibility elements:
        buttons, input fields, checkboxes, list items, and tabs.
        """
        if not UIA_AVAILABLE:
            return {"success": False, "error": "uiautomation library is not available."}

        try:
            root = auto.GetForegroundControl()
            if not root:
                root = auto.GetRootControl()

            if not root:
                return {"success": False, "error": "No control detected."}

            elements: List[Dict[str, Any]] = []

            def walk_tree(control, depth):
                if depth > max_depth or len(elements) >= 50:
                    return

                try:
                    name = control.Name or ""
                    c_type = control.ControlTypeName or ""
                    auto_id = control.AutomationId or ""
                    rect = control.BoundingRectangle  # Rect(left, top, right, bottom)

                    # Filter for interactive controls
                    interactive_types = {
                        "ButtonControl", "EditControl", "HyperlinkControl", "CheckBoxControl",
                        "RadioButtonControl", "ComboBoxControl", "ListItemControl", "TabItemControl",
                        "MenuItemControl"
                    }

                    if c_type in interactive_types or (name and rect.width() > 0 and rect.height() > 0):
                        elements.append({
                            "name": name.strip(),
                            "control_type": c_type.replace("Control", ""),
                            "automation_id": auto_id.strip(),
                            "is_enabled": getattr(control, "IsEnabled", True),
                            "bounds": {
                                "left": rect.left,
                                "top": rect.top,
                                "right": rect.right,
                                "bottom": rect.bottom,
                                "center_x": rect.left + rect.width() // 2,
                                "center_y": rect.top + rect.height() // 2,
                                "width": rect.width(),
                                "height": rect.height()
                            }
                        })

                    for child in control.GetChildren():
                        walk_tree(child, depth + 1)
                except Exception:
                    pass

            walk_tree(root, 1)

            return {
                "success": True,
                "window_name": root.Name or "Unknown",
                "element_count": len(elements),
                "elements": elements
            }
        except Exception as e:
            logger.error(f"UI Automation inspection error: {e}")
            return {"success": False, "error": str(e)}

    def find_control(
        self,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None
    ) -> Optional[Any]:
        """Finds a control in the active window matching criteria."""
        if not UIA_AVAILABLE:
            return None

        try:
            root = auto.GetForegroundControl()
            if not root:
                return None

            q_name = name.lower().strip() if name else None

            def search(control, depth=0):
                if depth > 4:
                    return None

                try:
                    c_name = (control.Name or "").lower()
                    c_type = control.ControlTypeName or ""
                    c_id = control.AutomationId or ""

                    match = True
                    if q_name and q_name not in c_name:
                        match = False
                    if control_type and control_type.lower() not in c_type.lower():
                        match = False
                    if automation_id and automation_id.lower() != c_id.lower():
                        match = False

                    if match and (control.BoundingRectangle.width() > 0):
                        return control

                    for child in control.GetChildren():
                        found = search(child, depth + 1)
                        if found:
                            return found
                except Exception:
                    pass
                return None

            return search(root)
        except Exception as e:
            logger.warning(f"Error searching control: {e}")
            return None

    def click_element_by_name(self, name: str, control_type: Optional[str] = None) -> Dict[str, Any]:
        """Finds an element by name and invokes or clicks it via UI Automation."""
        if not UIA_AVAILABLE:
            return {"success": False, "error": "UIA unavailable."}

        ctrl = self.find_control(name=name, control_type=control_type)
        if not ctrl:
            return {
                "success": False,
                "error": f"Element '{name}' (type: {control_type or 'any'}) not found in active window."
            }

        try:
            rect = ctrl.BoundingRectangle
            cx = rect.left + rect.width() // 2
            cy = rect.top + rect.height() // 2

            # Try native InvokePattern first (pure accessibility click, no cursor jump)
            invoke_pattern = getattr(ctrl, "GetInvokePattern", None)
            if invoke_pattern and callable(invoke_pattern):
                try:
                    pat = invoke_pattern()
                    if pat:
                        pat.Invoke()
                        return {
                            "success": True,
                            "method": "InvokePattern",
                            "name": ctrl.Name,
                            "center": (cx, cy)
                        }
                except Exception:
                    pass

            # Fallback to Click via UIA
            ctrl.Click(simulateMove=False)
            return {
                "success": True,
                "method": "UIA.Click",
                "name": ctrl.Name,
                "center": (cx, cy)
            }
        except Exception as e:
            logger.error(f"Failed to click element '{name}': {e}")
            return {"success": False, "error": str(e)}

    def type_into_element(self, text: str, name: Optional[str] = None, clear_first: bool = False) -> Dict[str, Any]:
        """Sets or types text into an input field using ValuePattern or SendKeys."""
        if not UIA_AVAILABLE:
            return {"success": False, "error": "UIA unavailable."}

        ctrl = None
        if name:
            ctrl = self.find_control(name=name, control_type="Edit")

        if not ctrl:
            # Fallback to focused control
            ctrl = auto.GetFocusedControl()

        if not ctrl:
            return {"success": False, "error": "No edit control found or focused."}

        try:
            ctrl.SetFocus()

            # Try ValuePattern
            val_pattern = getattr(ctrl, "GetValuePattern", None)
            if val_pattern and callable(val_pattern):
                try:
                    pat = val_pattern()
                    if pat:
                        pat.SetValue(text)
                        return {
                            "success": True,
                            "method": "ValuePattern",
                            "name": ctrl.Name,
                            "text": text
                        }
                except Exception:
                    pass

            # Fallback: SendKeys
            if clear_first:
                auto.SendKeys("{Ctrl}a{Delete}")
            auto.SendKeys(text)
            return {
                "success": True,
                "method": "SendKeys",
                "name": ctrl.Name,
                "text": text
            }
        except Exception as e:
            logger.error(f"Failed to type text into element: {e}")
            return {"success": False, "error": str(e)}


# Global singleton instance
native_uia = NativeUIAutomationEngine()
